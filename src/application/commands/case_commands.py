"""Command handlers for case-related operations."""

from datetime import UTC, datetime
from uuid import uuid4

from src.application.dtos.case_dtos import (
    AcceptCaseCommand,
    BookAppointmentCommand,
    GenerateEmailDraftCommand,
    ResolveCaseCommand,
    SendEmailCommand,
    StartSupportingCommand,
    SubmitCaseReviewCommand,
    TriggerDraftCommand,
    TriggerDraftDTO,
    UpdateEmailCommand,
)
from src.application.interfaces.background_queue import BackgroundTaskQueue
from src.application.interfaces.event_publisher import EventPublisher
from src.core.logger import logger
from src.domain.entities.intervention_email import InterventionEmail
from src.domain.entities.job import Job
from src.domain.exceptions import (
    CaseAlreadyClosedError,
    CaseNotFoundError,
    EmailUnavailableError,
    InvalidActionError,
    JobNotFoundError,
    UserIsNotAnAdvisorError,
)
from src.domain.repositories.advisor_repository import AdvisorRepository
from src.domain.repositories.case_repository import CaseRepository
from src.domain.repositories.email_repository import EmailRepository
from src.domain.repositories.job_repository import JobRepository
from src.domain.repositories.student_repository import StudentRepository
from src.domain.services.email_drafting import EmailDraftingService
from src.domain.value_objects.student_satisfaction import StudentSatisfaction


class CaseCommandHandler:
    """Handler for case-related commands."""

    def __init__(
        self,
        student_repo: StudentRepository,
        email_repo: EmailRepository,
        case_repo: CaseRepository,
        advisor_repo: AdvisorRepository,
        job_repo: JobRepository,
        task_queue: BackgroundTaskQueue,
        event_publisher: EventPublisher,
        email_drafting_service: EmailDraftingService,
    ) -> None:
        """Initialize the handler with required dependencies."""
        self.student_repo = student_repo
        self.email_repo = email_repo
        self.case_repo = case_repo
        self.advisor_repo = advisor_repo
        self.job_repo = job_repo
        self.email_drafting_service = email_drafting_service
        self.task_queue = task_queue
        self.event_publisher = event_publisher

    async def handle_accept_case(self, command: AcceptCaseCommand) -> None:
        """Try assign a case to an advisor."""
        case = await self.case_repo.get_by_id(command.case_id)

        advisor = await self.advisor_repo.find_by_user_id(command.user_id)
        if advisor is None:
            raise UserIsNotAnAdvisorError(command.user_id)

        case.assign_advisor(advisor.advisor_id, command.accepted_at)

        await self.case_repo.save(case)

        # Dispatch events via publisher
        await self.event_publisher.publish(case.domain_events)
        case.clear_events()

        new_email = InterventionEmail(case_id=case.case_id)
        await self.email_repo.add(new_email)

    async def handle_trigger_draft(
        self,
        command: TriggerDraftCommand,
    ) -> TriggerDraftDTO:
        """Execute the trigger draft command."""
        advisor = await self.advisor_repo.find_by_user_id(command.user_id)
        if advisor is None:
            raise UserIsNotAnAdvisorError(command.user_id)

        case = await self.case_repo.get_by_id(command.case_id)
        if case.assigned_advisor_id != advisor.advisor_id:
            raise CaseNotFoundError(case_id=case.case_id)

        if not case.can_generate_draft():
            raise InvalidActionError(
                'Current case state does not allow email generation.',
            )
        # 1. Check for existing email record for this case
        existing_email = await self.email_repo.get_by_case(case.case_id)
        if existing_email.is_generating:
            # Already in progress, just find the job_id
            try:
                active_job = await self.job_repo.get_by_correlation_id(
                    case.case_id,
                    'email_draft',
                )
            except JobNotFoundError:
                logger.error(
                    f'Inconsistency: Email {existing_email.email_id} says generating but no job found.',
                )
                raise
            return TriggerDraftDTO(
                job_id=active_job.job_id,
                status=active_job.status,
                is_new_job=False,
            )

        existing_email.prepare_for_regeneration()
        existing_email.mark_as_generating()
        await self.email_repo.save(existing_email)

        job_id = uuid4()
        new_job = Job(
            job_id=job_id,
            correlation_id=case.case_id,
            correlation_type='email_draft',
            created_at=datetime.now(UTC),
        )
        await self.job_repo.add(new_job)

        # 3. Queue the job
        await self.task_queue.enqueue(
            'run_email_draft_task',
            job_id=job_id,
            case_id=case.case_id,
            booking_link=command.booking_link,
            user_id=command.user_id,
        )

        return TriggerDraftDTO(
            job_id=new_job.job_id,
            status=new_job.status,
            is_new_job=True,
        )

    async def handle_send_email(self, command: SendEmailCommand) -> str:
        """Execute the send email command."""
        advisor = await self.advisor_repo.find_by_user_id(command.user_id)
        if advisor is None:
            raise UserIsNotAnAdvisorError(command.user_id)

        case = await self.case_repo.get_by_id(command.case_id)
        if case.assigned_advisor_id != advisor.advisor_id:
            raise CaseNotFoundError(case_id=case.case_id)

        if not case.is_active:
            raise CaseAlreadyClosedError(command.case_id)

        email = await self.email_repo.find_by_case(case_id=case.case_id)
        if email is None or not email.is_ready_to_send:
            raise EmailUnavailableError(case.case_id)

        # 1. Fetch student PII to get email
        student = await self.student_repo.get_by_id(case.sid)

        recipient_email = student.email

        job_id = uuid4()
        new_job = Job(
            job_id=job_id,
            correlation_id=case.case_id,
            correlation_type='email_draft',
            created_at=datetime.now(UTC),
        )

        await self.task_queue.enqueue(
            'run_dispatch_email_task',
            case_id=case.case_id,
            body=command.body,
            target_email=recipient_email,
        )
        await self.job_repo.add(new_job)

        # 4. Return recipient email for dispatching
        return recipient_email

    async def handle_update_email(self, command: UpdateEmailCommand) -> None:
        """Execute the update email command."""
        advisor = await self.advisor_repo.find_by_user_id(command.user_id)
        if advisor is None:
            raise UserIsNotAnAdvisorError(command.user_id)

        case = await self.case_repo.get_by_id(command.case_id)
        if case.assigned_advisor_id != advisor.advisor_id:
            raise CaseNotFoundError(case_id=case.case_id)

        email = await self.email_repo.find_by_case(case_id=case.case_id)
        if email is None:
            raise EmailUnavailableError(case.case_id)

        # Merge partial updates
        new_subject = command.subject if command.subject is not None else email.subject
        new_body = command.body if command.body is not None else email.body

        # Update the entity
        email.update_draft(new_subject or '', new_body or '')

        await self.email_repo.save(email)

    async def handle_generate_email_draft(
        self,
        command: GenerateEmailDraftCommand,
    ) -> None:
        """Execute the generate email draft command (Worker task logic)."""
        logger.info(f'Generating email draft for case {command.case_id}')

        # 1. Fetch case and student info
        case = await self.case_repo.get_by_id(command.case_id)
        email = await self.email_repo.get_by_case(case.case_id)
        email.mark_as_generating()
        await self.email_repo.save(email)

        student_data = await self.student_repo.get_by_id(case.sid)

        # 2. Fetch performance data
        perf_raw = await self.student_repo.get_recent_performance(case.sid)
        history_lines = [
            f'Year {p["yr"]} Sem {p["sem"]} Week {p["wk"]}: Score {p["score"]} ({p["status"]})'
            for p in perf_raw
        ]
        context_str = 'Trend: ' + ' | '.join(history_lines)

        # 3. Generate via AI port
        booking_link = command.booking_link or 'https://calendly.com/advisor-help'
        personalized_body = await self.email_drafting_service.generate_draft(
            student_data.student_name or '',
            context_str,
            booking_link,
        )

        # 4. Persistent storage: Update the existing placeholder
        email.set_draft_content(
            'Checking in on your academic progress',
            personalized_body,
        )
        await self.email_repo.save(email)

    async def handle_book_appointment(self, command: BookAppointmentCommand) -> None:
        """Record that a student has booked an appointment for their case."""
        case = await self.case_repo.get_by_id(command.case_id)
        if not case:
            raise CaseNotFoundError(command.case_id)

        case.record_booking()

        await self.case_repo.save(case)

        # Dispatch events via publisher
        await self.event_publisher.publish(case.domain_events)
        case.clear_events()

    async def handle_start_supporting(self, command: StartSupportingCommand) -> None:
        """Advisor starts supporting the student after they booked."""
        advisor = await self.advisor_repo.find_by_user_id(command.user_id)
        if advisor is None:
            raise UserIsNotAnAdvisorError(command.user_id)

        case = await self.case_repo.get_by_id(command.case_id)
        if case.assigned_advisor_id != advisor.advisor_id:
            raise CaseNotFoundError(case_id=case.case_id)

        case.start_supporting()

        await self.case_repo.save(case)

        # Dispatch events via publisher
        await self.event_publisher.publish(case.domain_events)
        case.clear_events()

    async def handle_resolve_case(self, command: ResolveCaseCommand) -> None:
        """Advisor marks the case as pending review."""
        advisor = await self.advisor_repo.find_by_user_id(command.user_id)
        if advisor is None:
            raise UserIsNotAnAdvisorError(command.user_id)

        case = await self.case_repo.get_by_id(command.case_id)
        if case.assigned_advisor_id != advisor.advisor_id:
            raise CaseNotFoundError(case_id=case.case_id)

        case.request_resolution(datetime.now(UTC))

        await self.case_repo.save(case)

        # Dispatch events via publisher
        await self.event_publisher.publish(case.domain_events)
        case.clear_events()

    async def handle_submit_case_review(self, command: SubmitCaseReviewCommand) -> None:
        """Finalize the case resolution based on student review."""
        case = await self.case_repo.get_by_id(command.case_id)
        if not case:
            raise CaseNotFoundError(command.case_id)

        is_failed = command.satisfaction in (
            StudentSatisfaction.BAD,
            StudentSatisfaction.VERY_BAD,
        )

        case.finalize_resolution(
            datetime.now(UTC),
            satisfaction=command.satisfaction,
            comment=command.comment,
            is_failed=is_failed,
        )

        await self.case_repo.save(case)

        # Dispatch events via publisher (CaseResolvedEvent or CaseFailedEvent)
        await self.event_publisher.publish(case.domain_events)
        case.clear_events()
