"""Command handlers for case-related operations."""

from datetime import UTC, datetime
from string import Template

import structlog

from src.application.dtos.case_dtos import (
    AcceptCaseCommand,
    BookAppointmentCommand,
    GenerateEmailDraftCommand,
    ResolveCaseCommand,
    SendEmailCommand,
    SendEmailResponseDTO,
    StartSupportingCommand,
    SubmitCaseReviewCommand,
    TriggerDraftCommand,
    TriggerDraftDTO,
    UpdateEmailCommand,
)
from src.application.interfaces.unit_of_work import UnitOfWork
from src.core.identifiers import generate_uuid
from src.domain.entities.intervention_email import InterventionEmail
from src.domain.entities.job import Job
from src.domain.exceptions import (
    CaseAlreadyClosedError,
    CaseNotFoundError,
    DraftGenerationError,
    EmailUnavailableError,
    InvalidActionError,
    JobNotFoundError,
    MissingPerformanceDataError,
    StudentNameMissingError,
    TimeSlotUnavailableError,
    UserIsNotAnAdvisorError,
)
from src.domain.services.availability import AdvisorAvailabilityService
from src.domain.services.email_drafting import EmailDraftingService
from src.domain.value_objects.student_satisfaction import StudentSatisfaction

logger = structlog.get_logger(__name__)
# Application-level safe fallbacks
SAFE_SUBJECT = 'Checking in on your academic progress'
SAFE_BODY = Template(
    'Hi ${student_name},\n\n'
    'I noticed a change in your recent course activity and wanted to check in to see how things are going. '
    'We are here to support you and help you navigate any challenges you might be facing.\n\n'
    'If you have a moment, I would love to chat and see how we can help. ',
)


class CaseCommandHandler:
    """Handler for case-related operations."""

    def __init__(
        self,
        uow: UnitOfWork,
        availability_service: AdvisorAvailabilityService,
        email_drafting_service: EmailDraftingService,
    ) -> None:
        """Initialize the handler with required dependencies."""
        self.uow = uow
        self.email_drafting_service = email_drafting_service
        self.availability_service = availability_service

    async def handle_accept_case(self, command: AcceptCaseCommand) -> None:
        """Try assign a case to an advisor."""
        async with self.uow:
            case = await self.uow.cases.get_by_id(command.case_id)

            advisor = await self.uow.advisors.find_by_user_id(command.user_id)
            if advisor is None:
                raise UserIsNotAnAdvisorError(command.user_id)

            case.assign_advisor(advisor.advisor_id, command.accepted_at)

            # Ensure email record is created before events are published
            new_email = InterventionEmail(case_id=case.case_id)
            await self.uow.emails.add(new_email)

            await self.uow.cases.save(case)
            await self.uow.commit()

    async def handle_trigger_draft(
        self,
        command: TriggerDraftCommand,
    ) -> TriggerDraftDTO:
        """Execute the trigger draft command."""
        async with self.uow:
            advisor = await self.uow.advisors.find_by_user_id(command.user_id)
            if advisor is None:
                raise UserIsNotAnAdvisorError(command.user_id)

            case = await self.uow.cases.get_by_id(command.case_id)
            if case.assigned_advisor_id != advisor.advisor_id:
                raise CaseNotFoundError(case_id=case.case_id)

            if not case.can_generate_draft():
                raise InvalidActionError(
                    'Current case state does not allow email generation.',
                )
            # 1. Check for existing email record for this case
            existing_email = await self.uow.emails.get_by_case(case.case_id)
            if existing_email.is_generating:
                # Already in progress, just find the job_id
                try:
                    active_job = await self.uow.jobs.get_by_correlation_id(
                        case.case_id,
                        'email_draft',
                    )
                except JobNotFoundError:
                    logger.error(
                        'Inconsistency: Email says generating but no job found',
                        email_id=str(existing_email.email_id),
                    )
                    raise
                return TriggerDraftDTO(
                    job_id=active_job.job_id,
                    status=active_job.status,
                    is_new_job=False,
                )

            existing_email.prepare_for_regeneration()
            existing_email.mark_as_generating()
            await self.uow.emails.save(existing_email)

            job_id = generate_uuid()
            new_job = Job(
                job_id=job_id,
                correlation_id=case.case_id,
                correlation_type='email_draft',
                created_at=datetime.now(UTC),
            )
            await self.uow.jobs.add(new_job)

            case.request_email_draft(
                job_id=job_id,
                user_id=command.user_id,
            )

            await self.uow.cases.save(case)
            await self.uow.commit()

            return TriggerDraftDTO(
                job_id=new_job.job_id,
                status=new_job.status,
                is_new_job=True,
            )

    async def handle_send_email(
        self,
        command: SendEmailCommand,
    ) -> SendEmailResponseDTO:
        """Execute the send email command."""
        async with self.uow:
            advisor = await self.uow.advisors.find_by_user_id(command.user_id)
            if advisor is None:
                raise UserIsNotAnAdvisorError(command.user_id)

            case = await self.uow.cases.get_by_id(command.case_id)
            if case.assigned_advisor_id != advisor.advisor_id:
                raise CaseNotFoundError(case_id=case.case_id)

            if not case.is_active:
                raise CaseAlreadyClosedError(command.case_id)

            email = await self.uow.emails.find_by_case(case_id=case.case_id)
            if email is None or not email.is_ready_to_send:
                raise EmailUnavailableError(case.case_id)

            # 1. Fetch student PII to get email
            student = await self.uow.students.get_by_id(case.sid)
            recipient_email = student.email

            # 2. Track as Job
            job_id = generate_uuid()
            new_job = Job(
                job_id=job_id,
                correlation_id=case.case_id,
                correlation_type='email_send',
                created_at=datetime.now(UTC),
            )
            await self.uow.jobs.add(new_job)

            case.record_email_sent(job_id=job_id, user_id=command.user_id)
            await self.uow.cases.save(case=case)
            await self.uow.commit()

            return SendEmailResponseDTO(
                job_id=job_id,
                status=new_job.status,
                recipient=recipient_email,
            )

    async def handle_update_email(self, command: UpdateEmailCommand) -> None:
        """Execute the update email command."""
        async with self.uow:
            advisor = await self.uow.advisors.find_by_user_id(command.user_id)
            if advisor is None:
                raise UserIsNotAnAdvisorError(command.user_id)

            case = await self.uow.cases.get_by_id(command.case_id)
            if case.assigned_advisor_id != advisor.advisor_id:
                raise CaseNotFoundError(case_id=case.case_id)

            email = await self.uow.emails.find_by_case(case_id=case.case_id)
            if email is None:
                raise EmailUnavailableError(case.case_id)

            # Merge partial updates
            new_subject = (
                command.subject if command.subject is not None else email.subject
            )
            new_body = command.body if command.body is not None else email.body

            # Update the entity
            email.update_draft(new_subject or '', new_body or '')

            await self.uow.emails.save(email)
            await self.uow.commit()

    async def handle_generate_email_draft(
        self,
        command: GenerateEmailDraftCommand,
    ) -> None:
        """Execute the generate email draft command (Worker task logic)."""
        logger.info('Generating email draft', case_id=str(command.case_id))

        async with self.uow:
            # 1. Fetch case and student info
            case = await self.uow.cases.get_by_id(command.case_id)
            email = await self.uow.emails.get_by_case(case.case_id)
            email.mark_as_generating()
            await self.uow.emails.save(email)

            student_data = await self.uow.students.get_by_id(case.sid)
            if not student_data.student_name:
                raise StudentNameMissingError(case.sid)

            # 2. Fetch performance data (Deterministic Fetching)
            perf_raw = await self.uow.students.get_recent_performance(case.sid)
            if not perf_raw:
                raise MissingPerformanceDataError(case.sid)

            history_lines = [
                f'Year {p["yr"]} Sem {p["sem"]} Week {p["wk"]}: Score {p["score"]} ({p["status"]})'
                for p in perf_raw
            ]
            context_str = 'Trend: ' + ' | '.join(history_lines)

            try:
                (
                    subject,
                    personalized_body,
                ) = await self.email_drafting_service.generate_draft(
                    student_data.student_name,
                    context_str,
                )
            except DraftGenerationError as e:
                logger.warning(
                    'Draft generation failed, falling back to safe template',
                    case_id=str(command.case_id),
                    error=str(e),
                )
                subject = SAFE_SUBJECT
                personalized_body = SAFE_BODY.safe_substitute(
                    student_name=student_data.student_name,
                )

            # 4. Persistent storage: Update the existing placeholder
            email.set_draft_content(
                subject,
                personalized_body,
            )
            await self.uow.emails.save(email)
            await self.uow.commit()

    async def handle_book_appointment(self, command: BookAppointmentCommand) -> None:
        """Record that a student has booked an appointment for their case."""
        async with self.uow:
            case = await self.uow.cases.get_by_id(command.case_id)

            # Enforce advisor availability if assigned
            if case.assigned_advisor_id is not None:
                is_available = await self.availability_service.is_slot_available(
                    case.assigned_advisor_id,
                    command.appointment_time,
                    duration_minutes=command.duration_minutes,
                )
                if not is_available:
                    raise TimeSlotUnavailableError(
                        case.assigned_advisor_id,
                        command.appointment_time,
                    )

            case.record_booking(
                appointment_time=command.appointment_time,
                meeting_method=command.meeting_method,
                duration_minutes=command.duration_minutes,
                notes=command.notes,
            )

            await self.uow.cases.save(case)
            await self.uow.commit()

    async def handle_start_supporting(self, command: StartSupportingCommand) -> None:
        """Advisor starts supporting the student after they booked."""
        async with self.uow:
            advisor = await self.uow.advisors.find_by_user_id(command.user_id)
            if advisor is None:
                raise UserIsNotAnAdvisorError(command.user_id)

            case = await self.uow.cases.get_by_id(command.case_id)
            if case.assigned_advisor_id != advisor.advisor_id:
                raise CaseNotFoundError(case_id=case.case_id)

            case.start_supporting()

            await self.uow.cases.save(case)
            await self.uow.commit()

    async def handle_resolve_case(self, command: ResolveCaseCommand) -> None:
        """Advisor marks the case as pending review."""
        async with self.uow:
            advisor = await self.uow.advisors.find_by_user_id(command.user_id)
            if advisor is None:
                raise UserIsNotAnAdvisorError(command.user_id)

            case = await self.uow.cases.get_by_id(command.case_id)
            if case.assigned_advisor_id != advisor.advisor_id:
                raise CaseNotFoundError(case_id=case.case_id)

            case.request_resolution(datetime.now(UTC))

            await self.uow.cases.save(case)
            await self.uow.commit()

    async def handle_submit_case_review(self, command: SubmitCaseReviewCommand) -> None:
        """Finalize the case resolution based on student review."""
        async with self.uow:
            case = await self.uow.cases.get_by_id(command.case_id)
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

            await self.uow.cases.save(case)
            await self.uow.commit()
