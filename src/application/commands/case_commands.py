"""Command handlers for case-related operations."""

from datetime import UTC, datetime
from uuid import uuid4

from src.application.dtos.case_dtos import (
    AcceptCaseCommand,
    GenerateEmailDraftCommand,
    SendEmailCommand,
    TriggerDraftCommand,
    TriggerDraftDTO,
)
from src.application.interfaces.background_queue import BackgroundTaskQueue
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
from src.domain.repositories.badge_repository import BadgeRepository
from src.domain.repositories.case_repository import CaseRepository
from src.domain.repositories.email_repository import EmailRepository
from src.domain.repositories.job_repository import JobRepository
from src.domain.repositories.point_ledger_repository import PointLedgerRepository
from src.domain.repositories.student_repository import StudentRepository
from src.domain.services.email_drafting import EmailDraftingService
from src.domain.services.gamification import GamificationService


class CaseCommandHandler:
    """Handler for case-related commands."""

    def __init__(
        self,
        student_repo: StudentRepository,
        email_repo: EmailRepository,
        case_repo: CaseRepository,
        advisor_repo: AdvisorRepository,
        job_repo: JobRepository,
        gamification_service: GamificationService,
        task_queue: BackgroundTaskQueue,
        point_ledger_repo: PointLedgerRepository,
        email_drafting_service: EmailDraftingService,
        badge_repo: BadgeRepository | None = None,
    ) -> None:
        """Initialize the handler with required dependencies."""
        self.student_repo = student_repo
        self.email_repo = email_repo
        self.case_repo = case_repo
        self.advisor_repo = advisor_repo
        self.job_repo = job_repo
        self.__point_ledger_repo = point_ledger_repo
        self.gamification_service = gamification_service
        self.email_drafting_service = email_drafting_service
        self.task_queue = task_queue
        self.badge_repo = badge_repo

    async def handle_accept_case(self, command: AcceptCaseCommand) -> None:
        """Try assign a case to an advisor."""
        case = await self.case_repo.get_by_id(command.case_id)

        advisor = await self.advisor_repo.find_by_user_id(command.user_id)
        if advisor is None:
            raise UserIsNotAnAdvisorError(command.user_id)

        case.assign_advisor(advisor.advisor_id, command.accepted_at)

        await self.case_repo.save(case)

        student = await self.student_repo.get_by_id(case.sid)

        points = self.gamification_service.calculate_points(
            GamificationService.Action.ACCEPT_TASK,
            case.assigned_at,
            student.current_risk_status,
        )

        ledger = await self.__point_ledger_repo.get_by_advisor_id(advisor.advisor_id)
        ledger.award_points(
            case_id=case.case_id,
            action='accept_case',
            points=points,
            earned_at=datetime.now(UTC),
        )
        await self.__point_ledger_repo.save(ledger)

        # if command.auto_generate_draft_email:
        #     for sid, case_id in new_sids:
        #         trigger_command = TriggerDraftCommand(
        #             case_id=case_id,
        #             user_id=user_id,
        #             update_db=False,
        #         )
        #         job_id = await self.case_command_handler.handle_trigger_draft(
        #             trigger_command,
        #         )
        #         triggered_jobs.append({'sid': sid, 'job_id': job_id})
        #         db_updates.append((job_id, 'email_draft', case_id, 'case'))
        #
        # Batch create job tracking records

    # async def handle_update_status(self, command: UpdateStudentStatusCommand) -> None:
    #     """Execute the status update command."""
    #     case = await self.case_repo.get_by_id(command.case_id)
    #     if not case:
    #         raise ValueError(f'Case {command.case_id} not found.')
    #
    #     await self.student_repo.update_intervention_status(case.sid, command.status)
    #
    #     now = datetime.now(UTC)
    #
    #     # Case transition logic
    #     if command.status == InterventionStatus.RESOLVED:
    #         case.resolve(now)
    #     elif command.status in (
    #         InterventionStatus.EXPIRED,
    #         InterventionStatus.DISMISSED,
    #     ):
    #         case.fail(now)
    #
    #     await self.case_repo.save(case)

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
        existing_email = await self.email_repo.find_by_case(case.case_id)
        if existing_email and existing_email.is_generating:
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

        # 2. Create/Update placeholder entry in intervention_emails
        if not existing_email:
            existing_email = InterventionEmail(case_id=case.case_id)
            existing_email.mark_as_generating()
            await self.email_repo.add(existing_email)
        else:
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
