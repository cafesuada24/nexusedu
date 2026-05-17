"""Command handlers for case-related operations."""

from datetime import UTC, datetime

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
from src.domain.entities.notification import Notification
from src.domain.exceptions import (
    AdvisorNotFoundError,
    CaseAlreadyClosedError,
    CaseNotFoundError,
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
from src.domain.value_objects.status import (
    NotificationPriority,
    NotificationType,
)
from src.domain.value_objects.student_satisfaction import StudentSatisfaction

logger = structlog.get_logger(__name__)


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

            # Capture initial GPA snapshot
            recent_perf = await self.uow.students.get_recent_performance(case.sid)
            if recent_perf:
                # Calculate average of recent scores as initial GPA proxy
                avg_score = sum(p['score'] for p in recent_perf) / len(recent_perf)
                case.set_initial_gpa(avg_score)

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

            # Mark as nudge if it's the first interaction
            if case.first_interaction_at is None:
                email.is_nudge = True

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

        try:
            async with self.uow:
                # 1. Fetch case and student info
                case = await self.uow.cases.get_by_id(command.case_id)
                email = await self.uow.emails.get_by_case(case.case_id)
                email.mark_as_generating()
                await self.uow.emails.save(email)

                student_data = await self.uow.students.get_by_id(case.sid)
                if not student_data.student_name:
                    raise StudentNameMissingError(case.sid)

                # Fetch advisor and their settings for personalized AI tone and rules
                if not case.assigned_advisor_id:
                    raise AdvisorNotFoundError('No advisor assigned to this case.')

                advisor = await self.uow.advisors.get_by_id(case.assigned_advisor_id)
                settings = await self.uow.user_settings.get_by_user_id(advisor.user_id)

                # 2. Fetch performance data (Deterministic Fetching)
                perf_raw = await self.uow.students.get_recent_performance(case.sid)
                if not perf_raw:
                    raise MissingPerformanceDataError(case.sid)

                history_lines = [
                    f'Year {p["yr"]} Sem {p["sem"]} Week {p["wk"]}: Score {p["score"]} ({p["status"]})'
                    for p in perf_raw
                ]
                context_str = 'Trend: ' + ' | '.join(history_lines)

                # 3. Structural Generation
                (
                    subject,
                    personalized_body,
                ) = await self.email_drafting_service.generate_draft(
                    student_data.student_name,
                    context_str,
                    ai_tone=settings.ai_tone,
                    safety_rules=settings.safety_rules,
                )

                # 4. Persistent storage: Update the existing placeholder
                email.set_draft_content(
                    subject,
                    personalized_body,
                )
                await self.uow.emails.save(email)
                await self.uow.commit()
        except Exception as e:
            logger.error(
                'Email draft generation failed, reverting state',
                case_id=str(command.case_id),
                error=str(e),
            )
            async with self.uow:
                email = await self.uow.emails.get_by_case(command.case_id)
                email.prepare_for_regeneration()
                await self.uow.emails.save(email)
                await self.uow.commit()
            raise

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

            # Notify the assigned advisor
            if case.assigned_advisor_id:
                advisor = await self.uow.advisors.get_by_id(case.assigned_advisor_id)
                student = await self.uow.students.get_by_id(case.sid)
                notification = Notification(
                    user_id=advisor.user_id,
                    type=NotificationType.SUCCESS,
                    title='Student Booked Appointment',
                    body=f'Student {student.student_name} has booked an appointment for case {case.case_id}.',
                    priority=NotificationPriority.HIGH,
                    payload={
                        'case_id': str(case.case_id),
                        'appointment_time': command.appointment_time.isoformat(),
                    },
                )
                notification.create()
                await self.uow.notification.add(notification)

            # Record student response to nudge
            email = await self.uow.emails.find_by_case(case.case_id)
            if email and email.is_nudge and email.responded_at is None:
                email.responded_at = datetime.now(UTC)
                await self.uow.emails.save(email)

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

            # Capture final GPA snapshot
            final_gpa = None
            recent_perf = await self.uow.students.get_recent_performance(case.sid)
            if recent_perf:
                final_gpa = sum(p['score'] for p in recent_perf) / len(recent_perf)

            case.finalize_resolution(
                datetime.now(UTC),
                satisfaction=command.satisfaction,
                comment=command.comment,
                is_failed=is_failed,
                final_gpa=final_gpa,
            )

            # Notify the assigned advisor
            if case.assigned_advisor_id:
                advisor = await self.uow.advisors.get_by_id(case.assigned_advisor_id)
                student = await self.uow.students.get_by_id(case.sid)

                status_text = 'failed' if is_failed else 'resolved'
                notif_type = (
                    NotificationType.WARNING if is_failed else NotificationType.SUCCESS
                )

                notification = Notification(
                    user_id=advisor.user_id,
                    type=notif_type,
                    title=f'Case Review Submitted: {status_text.capitalize()}',
                    body=f'Student {student.student_name} has reviewed case {case.case_id} as {status_text}. Satisfaction: {command.satisfaction.value}.',
                    priority=NotificationPriority.NORMAL,
                    payload={
                        'case_id': str(case.case_id),
                        'satisfaction': command.satisfaction.value,
                        'is_failed': is_failed,
                    },
                )
                notification.create()
                await self.uow.notification.add(notification)

            await self.uow.cases.save(case)
            await self.uow.commit()
