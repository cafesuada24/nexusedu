"""Command handlers for alert-related operations."""

from dataclasses import dataclass
from uuid import UUID, uuid4

from src.application.interfaces.background_queue import BackgroundTaskQueue
from src.domain.repositories.advisor_repository import AdvisorRepository
from src.domain.repositories.alert_repository import AlertRepository
from src.domain.repositories.case_repository import CaseRepository
from src.domain.repositories.email_repository import EmailRepository
from src.domain.repositories.idempotency_repository import IdempotencyRepository
from src.domain.repositories.job_repository import JobRepository
from src.domain.repositories.student_repository import StudentRepository
from src.domain.services.email_drafting import EmailDraftingService
from src.domain.services.gamification import GamificationService
from src.domain.value_objects.status import CaseStatus, InterventionStatus, RiskStatus
from src.telemetry.logger import logger


@dataclass
class UpdateStudentStatusCommand:
    """Command to update a student's intervention status."""

    sid: UUID
    status: InterventionStatus
    user_id: UUID


@dataclass
class AwardReviewPointsCommand:
    """Command to award points for reviewing a draft."""

    sid: UUID
    user_id: UUID


@dataclass
class TriggerDraftCommand:
    """Command to trigger a background email draft generation."""

    sid: UUID
    user_id: UUID
    booking_link: str | None = None
    update_db: bool = True


@dataclass
class GenerateEmailDraftCommand:
    """Command to generate an email draft (intended for worker)."""

    sid: UUID
    job_id: UUID
    booking_link: str | None = None
    user_id: UUID | None = None


@dataclass
class SendEmailCommand:
    """Command to record and send an intervention email."""

    sid: UUID
    body: str
    user_id: UUID


class AlertCommandHandler:
    """Handler for alert-related commands."""

    def __init__(
        self,
        student_repo: StudentRepository,
        email_repo: EmailRepository,
        case_repo: CaseRepository,
        alert_repo: AlertRepository,
        advisor_repo: AdvisorRepository,
        idempotency_repo: IdempotencyRepository,
        job_repo: JobRepository,
        gamification_service: GamificationService,
        task_queue: BackgroundTaskQueue,
        email_drafting_service: EmailDraftingService | None = None,
    ) -> None:
        """Initialize the handler with required dependencies."""
        self.student_repo = student_repo
        self.email_repo = email_repo
        self.case_repo = case_repo
        self.alert_repo = alert_repo
        self.advisor_repo = advisor_repo
        self.idempotency_repo = idempotency_repo
        self.job_repo = job_repo
        self.gamification_service = gamification_service
        self.email_drafting_service = email_drafting_service
        self.task_queue = task_queue

    async def handle_update_status(self, command: UpdateStudentStatusCommand) -> None:
        """Execute the status update command."""
        await self.student_repo.update_intervention_status(command.sid, command.status)
        
        # Case transition logic
        if command.status in (InterventionStatus.RESOLVED, InterventionStatus.DISMISSED):
            active_case = await self.case_repo.get_active_case(command.sid)
            if active_case:
                await self.case_repo.update_case_status(
                    active_case.case_id, command.status.value
                )
        elif command.status != InterventionStatus.NONE:
            # If moving to an intervention status (NOTIFIED, BOOKED, etc.)
            # ensure an active case exists
            active_case = await self.case_repo.get_active_case(command.sid)
            if not active_case:
                from src.domain.entities.case import Case
                new_case = Case(sid=command.sid, status=CaseStatus.OPEN)
                await self.case_repo.create_case(new_case)

        # Gamification hooks for status changes
        if command.status == InterventionStatus.BOOKED:
            await self._award_points(command.user_id, command.sid, 'meeting_booked')
        elif command.status == InterventionStatus.RESOLVED:
            await self._award_points(command.user_id, command.sid, 'student_resolved')

    async def handle_award_review_points(
        self,
        command: AwardReviewPointsCommand,
    ) -> None:
        """Execute the award review points command."""
        await self._award_points(
            command.user_id,
            command.sid,
            'draft_reviewed',
        )

    async def handle_trigger_draft(self, command: TriggerDraftCommand) -> UUID:
        """Execute the trigger draft command."""
        # if not await self.task_queue.is_available():
        #     raise RuntimeError('Task queue is not available. Task cannot be enqueued.')

        active_case = await self.case_repo.get_active_case(command.sid)
        correlation_id = active_case.case_id if active_case else command.sid
        correlation_type = 'case' if active_case else 'student'

        job_id = uuid4()
        await self.task_queue.enqueue(
            'run_email_draft_task',
            job_id=str(job_id),
            sid=str(command.sid),
            booking_link=command.booking_link,
            user_id=str(command.user_id),
        )

        if command.update_db:
            await self.job_repo.create_job(
                job_id, 'email_draft', correlation_id, correlation_type
            )
        return job_id

    async def handle_generate_email_draft(
        self,
        command: GenerateEmailDraftCommand,
    ) -> None:
        """Execute the generate email draft command (Worker task logic)."""
        if not self.email_drafting_service:
            raise ValueError('EmailDraftingService not provided.')

        logger.info(f'Generating email draft for student {command.sid}')
        await self.job_repo.start_job(command.job_id)

        try:
            # 1. Fetch student PII
            student_data = await self.student_repo.get_pii(command.sid)
            if not student_data:
                raise ValueError(f'Student {command.sid} not found.')

            # 2. Fetch performance data
            perf_raw = await self.student_repo.get_recent_performance(command.sid)
            history_lines = [
                f'Year {p["yr"]} Sem {p["sem"]} Week {p["wk"]}: Score {p["score"]} ({p["status"]})'
                for p in perf_raw
            ]
            context_str = 'Trend: ' + ' | '.join(history_lines)

            # 3. Generate via AI port
            booking_link = command.booking_link or 'https://calendly.com/advisor-help'
            personalized_body = await self.email_drafting_service.generate_draft(
                student_data['student_name'],
                context_str,
                booking_link,
            )

            # 4. Persistent storage
            active_case = await self.case_repo.get_active_case(command.sid)
            await self.email_repo.create_draft(
                command.sid,
                command.user_id,
                'Checking in on your academic progress',
                personalized_body,
                case_id=active_case.case_id if active_case else None,
            )
            await self.job_repo.complete_job(command.job_id)
        except Exception as e:
            logger.error(f'Failed to generate email draft: {str(e)}')
            await self.job_repo.fail_job(command.job_id, str(e))
            raise e

    async def handle_send_email(self, command: SendEmailCommand) -> str:
        """Execute the send email command."""
        # 1. Fetch student PII to get email
        student_data = await self.student_repo.get_pii(command.sid)
        if not student_data:
            raise ValueError(f'Student {command.sid} not found.')

        recipient_email = student_data['email']

        # 2. Update states
        await self.student_repo.update_intervention_status(
            command.sid, InterventionStatus.SENT,
        )
        await self.email_repo.mark_as_sent(command.sid, command.body)
        await self.student_repo.update_last_notified(command.sid)

        # 3. Gamification
        await self._award_points(command.user_id, command.sid, 'email_sent')

        # 4. Return recipient email for dispatching
        return recipient_email

    async def _award_points(
        self,
        advisor_id: UUID,
        sid: UUID,
        action_type: str,
    ) -> None:
        """Orchestrate awarding points for an advisor action."""
        recorded_dt = await self.student_repo.get_latest_status_timestamp(sid)
        points = self.gamification_service.calculate_points(action_type, recorded_dt)
        if points > 0:
            await self.advisor_repo.record_points(advisor_id, sid, action_type, points)

    async def check_idempotency(self, key: UUID) -> bool:
        """Check if an idempotency key has been used."""
        return await self.idempotency_repo.check_key(key)

    async def record_idempotency(self, key: UUID) -> None:
        """Record a new idempotency key."""
        await self.idempotency_repo.record_key(key)
