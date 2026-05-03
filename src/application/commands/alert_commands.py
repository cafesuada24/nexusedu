"""Command handlers for alert-related operations."""

from dataclasses import dataclass
from typing import Any
from uuid import UUID, uuid4

from src.application.interfaces.background_queue import BackgroundTaskQueue
from src.core.logger import logger
from src.domain.repositories.advisor_repository import AdvisorRepository
from src.domain.repositories.alert_repository import AlertRepository
from src.domain.repositories.case_repository import CaseRepository
from src.domain.repositories.email_repository import EmailRepository
from src.domain.repositories.idempotency_repository import IdempotencyRepository
from src.domain.repositories.job_repository import JobRepository
from src.domain.repositories.student_repository import StudentRepository
from src.domain.services.email_drafting import EmailDraftingService
from src.domain.services.gamification import GamificationService
from src.domain.value_objects.status import (
    CaseStatus,
    EmailStatus,
    InterventionStatus,
    RiskStatus,
)


@dataclass
class UpdateStudentStatusCommand:
    """Command to update a student's intervention status."""

    case_id: UUID
    status: InterventionStatus
    user_id: UUID


@dataclass
class AwardReviewPointsCommand:
    """Command to award points for reviewing a draft."""

    case_id: UUID
    user_id: UUID


@dataclass
class TriggerDraftCommand:
    """Command to trigger a background email draft generation."""

    case_id: UUID
    user_id: UUID
    booking_link: str | None = None
    update_db: bool = True


@dataclass
class GenerateEmailDraftCommand:
    """Command to generate an email draft (intended for worker)."""

    case_id: UUID
    job_id: UUID
    booking_link: str | None = None
    user_id: UUID | None = None


@dataclass
class SendEmailCommand:
    """Command to record and send an intervention email."""

    case_id: UUID
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
        job_repo: JobRepository,
        gamification_service: GamificationService,
        task_queue: BackgroundTaskQueue,
        email_drafting_service: EmailDraftingService | None = None,
        badge_repo: Any | None = None,
    ) -> None:
        """Initialize the handler with required dependencies."""
        self.student_repo = student_repo
        self.email_repo = email_repo
        self.case_repo = case_repo
        self.alert_repo = alert_repo
        self.advisor_repo = advisor_repo
        self.job_repo = job_repo
        self.gamification_service = gamification_service
        self.email_drafting_service = email_drafting_service
        self.task_queue = task_queue
        self.badge_repo = badge_repo

    async def handle_update_status(self, command: UpdateStudentStatusCommand) -> None:
        """Execute the status update command."""
        case = await self.case_repo.get_by_id(command.case_id)
        if not case:
            raise ValueError(f'Case {command.case_id} not found.')

        await self.student_repo.update_intervention_status(case.sid, command.status)

        # Case transition logic
        if command.status in (
            InterventionStatus.RESOLVED,
            InterventionStatus.DISMISSED,
        ):
            await self.case_repo.update_case_status(case.case_id, command.status)
        elif (
            command.status != InterventionStatus.NONE and case.status != CaseStatus.OPEN
        ):
            await self.case_repo.update_case_status(case.case_id, CaseStatus.OPEN.value)

        # Gamification hooks for status changes
        if command.status == InterventionStatus.BOOKED:
            await self._award_points(command.user_id, case.sid, 'meeting_booked')
        elif command.status == InterventionStatus.RESOLVED:
            await self._award_points(command.user_id, case.sid, 'student_resolved')

    async def handle_award_review_points(
        self,
        command: AwardReviewPointsCommand,
    ) -> None:
        """Execute the award review points command."""
        case = await self.case_repo.get_by_id(command.case_id)
        if not case:
            raise ValueError(f'Case {command.case_id} not found.')

        await self._award_points(
            command.user_id,
            case.sid,
            'draft_reviewed',
        )

    async def handle_trigger_draft(self, command: TriggerDraftCommand) -> UUID:
        """Execute the trigger draft command."""
        case = await self.case_repo.get_by_id(command.case_id)
        if not case:
            raise ValueError(f'Case {command.case_id} not found.')

        # 1. Check for existing email record for this case
        existing_email = await self.email_repo.get_by_case(case.case_id)
        if existing_email:
            # If already generating or drafted, we might want to skip or just return current job
            # For now, we'll allow re-triggering by updating status back to generating
            # but usually, we'd check if it's already 'generating'.
            if existing_email.status.value == 'generating':
                # Already in progress, just find the job_id
                active_job = await self.job_repo.get_active_job(
                    case.case_id,
                    'case',
                    'email_draft',
                )
                if active_job:
                    return active_job

        # 2. Create/Update placeholder entry in intervention_emails
        if not existing_email:
            await self.email_repo.create_placeholder(
                case.case_id,
                case.sid,
                command.user_id,
            )
        else:
            await self.email_repo.update_content(
                case.case_id,
                '',
                '',
                EmailStatus.GENERATING,
            )

        # 3. Queue the job
        job_id = uuid4()
        await self.task_queue.enqueue(
            'run_email_draft_task',
            job_id=str(job_id),
            case_id=str(case.case_id),
            booking_link=command.booking_link,
            user_id=str(command.user_id),
        )

        if command.update_db:
            await self.job_repo.create_job(
                job_id,
                'email_draft',
                case.case_id,
                'case',
            )
        return job_id

    async def handle_generate_email_draft(
        self,
        command: GenerateEmailDraftCommand,
    ) -> None:
        """Execute the generate email draft command (Worker task logic)."""
        if not self.email_drafting_service:
            raise ValueError('EmailDraftingService not provided.')

        logger.info(f'Generating email draft for case {command.case_id}')
        await self.job_repo.start_job(command.job_id)

        try:
            # 1. Fetch case and student info
            case = await self.case_repo.get_by_id(command.case_id)
            if not case:
                raise ValueError(f'Case {command.case_id} not found.')

            student_data = await self.student_repo.get_pii(case.sid)
            if not student_data:
                raise ValueError(f'Student info for {case.sid} not found.')

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
                student_data['student_name'],
                context_str,
                booking_link,
            )

            # 4. Persistent storage: Update the existing placeholder
            await self.email_repo.update_content(
                case.case_id,
                'Checking in on your academic progress',
                personalized_body,
                EmailStatus.DRAFT,
            )
            await self.job_repo.complete_job(command.job_id)
        except Exception as e:
            logger.error(f'Failed to generate email draft: {str(e)}')
            await self.job_repo.fail_job(command.job_id, str(e))
            raise e

    async def handle_send_email(self, command: SendEmailCommand) -> str:
        """Execute the send email command."""
        case = await self.case_repo.get_by_id(command.case_id)
        if not case:
            raise ValueError(f'Case {command.case_id} not found.')

        # 1. Fetch student PII to get email
        student_data = await self.student_repo.get_pii(case.sid)
        if not student_data:
            raise ValueError(f'Student info for {case.sid} not found.')

        recipient_email = student_data['email']

        # 2. Database Write: Update existing email record for the case
        await self.student_repo.update_intervention_status(
            case.sid,
            InterventionStatus.SENT,
        )
        await self.email_repo.mark_as_sent(case.case_id, command.body)
        await self.student_repo.update_last_notified(case.sid)
        
        # Auto-assign the case to the advisor who sent the email
        assigned = await self.case_repo.assign_case(command.case_id, command.user_id)
        if not assigned:
            logger.info(
                f"Case {command.case_id} already assigned. Skipping auto-assignment for advisor {command.user_id}."
            )

        # 3. Gamification
        await self._award_points(command.user_id, case.sid, 'email_sent')

        # 4. Queue the actual email dispatch to ARQ worker
        await self.task_queue.enqueue(
            'run_dispatch_email_task',
            case_id=str(case.case_id),
            body=command.body,
            target_email=recipient_email,
        )

        # 5. Return recipient email for logging
        return recipient_email

    async def _award_points(
        self,
        advisor_id: UUID,
        sid: UUID,
        action_type: str,
    ) -> None:
        """Orchestrate awarding points for an advisor action."""
        if await self.advisor_repo.has_existing_action(advisor_id, sid, action_type):
            logger.info(
                f'Gamification: Action {action_type} already recorded for advisor {advisor_id} and student {sid}. Skipping.',
            )
            return

        recorded_dt = await self.student_repo.get_latest_status_timestamp(sid)

        student = await self.student_repo.get_by_id(sid)
        risk_level = RiskStatus.UNKNOWN
        if student:
            risk_level = student.current_risk_status

        points = self.gamification_service.calculate_points(
            action_type,
            recorded_dt,
            risk_level,
        )
        if points > 0:
            await self.advisor_repo.record_points(advisor_id, sid, action_type, points)
            if self.badge_repo:
                await self._check_and_award_badges(advisor_id)

    async def _check_and_award_badges(self, advisor_id: UUID) -> None:
        """Check and award badges based on updated stats."""
        # 1. Get current stats
        stats = await self.badge_repo.get_advisor_stats(advisor_id)
        
        # 2. Check eligible badges
        eligible_badges = self.gamification_service.check_badges(stats)
        
        # 3. Check what they already have
        existing_badges = await self.badge_repo.get_advisor_badges(advisor_id)
        
        # 4. Award new ones
        for badge_id in eligible_badges:
            if badge_id not in existing_badges:
                awarded = await self.badge_repo.award_badge(advisor_id, badge_id)
                if awarded:
                    logger.info(f'Gamification: Advisor {advisor_id} earned badge {badge_id}!')
