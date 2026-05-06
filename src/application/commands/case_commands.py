"""Command handlers for case-related operations."""

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from src.application.dtos.case_dtos import (
    AcceptCaseCommand,
    AwardReviewPointsCommand,
    GenerateEmailDraftCommand,
    SendEmailCommand,
    TriggerDraftCommand,
    UpdateStudentStatusCommand,
)
from src.application.interfaces.background_queue import BackgroundTaskQueue
from src.application.interfaces.ledger_query_service import PointLedgerQueryService
from src.core.logger import logger
from src.domain.exceptions import UserIsNotAnAdvisorError
from src.domain.repositories.advisor_repository import AdvisorRepository
from src.domain.repositories.badge_repository import BadgeRepository
from src.domain.repositories.case_repository import CaseRepository
from src.domain.repositories.email_repository import EmailRepository
from src.domain.repositories.job_repository import JobRepository
from src.domain.repositories.student_repository import StudentRepository
from src.domain.repositories.task_repository import TaskRepository
from src.domain.services.email_drafting import EmailDraftingService
from src.domain.services.gamification import GamificationService
from src.domain.value_objects.status import (
    EmailStatus,
    InterventionStatus,
    TaskType,
)


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
        point_ledger_query_service: PointLedgerQueryService,
        task_repo: TaskRepository | None = None,
        email_drafting_service: EmailDraftingService | None = None,
        badge_repo: BadgeRepository | None = None,
    ) -> None:
        """Initialize the handler with required dependencies."""
        self.student_repo = student_repo
        self.email_repo = email_repo
        self.case_repo = case_repo
        self.advisor_repo = advisor_repo
        self.job_repo = job_repo
        self.__point_ledger_query_service = point_ledger_query_service
        self.gamification_service = gamification_service
        self.email_drafting_service = email_drafting_service
        self.task_queue = task_queue
        self.badge_repo = badge_repo
        self.task_repo = task_repo

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

        await self.__point_ledger_query_service.award_points(
            advisor_id=advisor.advisor_id,
            task_id=uuid4(),
            points=points,
            earned_at=datetime.now(UTC),
        )

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

    async def _complete_task_by_type(
        self,
        case_id: UUID,
        task_type: TaskType,
        user_id: UUID,
    ) -> None:
        """Helper to find and complete a task of a specific type for a case."""
        # if not self.task_repo:
        #     return
        #
        # tasks = await self.task_repo.get_by_case(case_id)
        # for task in tasks:
        #     if task.action_type == task_type and task.status != TaskStatus.COMPLETED:
        #         await self.handle_complete_task(
        #             CompleteTaskCommand(task_id=task.task_id, user_id=user_id),
        #         )
        #         break

    async def handle_update_status(self, command: UpdateStudentStatusCommand) -> None:
        """Execute the status update command."""
        case = await self.case_repo.get_by_id(command.case_id)
        if not case:
            raise ValueError(f'Case {command.case_id} not found.')

        await self.student_repo.update_intervention_status(case.sid, command.status)

        now = datetime.now(UTC)

        # Case transition logic
        if command.status == InterventionStatus.RESOLVED:
            case.resolve(now)
        elif command.status in (
            InterventionStatus.EXPIRED,
            InterventionStatus.DISMISSED,
        ):
            case.fail(now)

        await self.case_repo.save(case)
        # Gamification hooks for status changes
        if command.status == InterventionStatus.BOOKED:
            await self._complete_task_by_type(
                case.case_id,
                TaskType.STUDENT_BOOK,
                command.user_id,
            )
        elif command.status == InterventionStatus.RESOLVED:
            await self._complete_task_by_type(
                case.case_id,
                TaskType.RESOLVE_CASE,
                command.user_id,
            )

    async def handle_award_review_points(
        self,
        command: AwardReviewPointsCommand,
    ) -> None:
        """Execute the award review points command."""
        await self._complete_task_by_type(
            command.case_id,
            TaskType.REVIEW_DRAFT,
            command.user_id,
        )

    async def handle_trigger_draft(self, command: TriggerDraftCommand) -> UUID:
        """Execute the trigger draft command."""
        case = await self.case_repo.get_by_id(command.case_id)
        advisor = await self.advisor_repo.find_by_user_id(command.user_id)
        if advisor is None:
            raise UserIsNotAnAdvisorError(command.user_id)


        # 1. Check for existing email record for this case
        existing_email = await self.email_repo.get_by_case(case.case_id)
        if existing_email and existing_email.status.value == 'generating':
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
                advisor.advisor_id,
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

        # TODO: refactor this stupid logic later
        advisor_id = await self._resolve_advisor_id(command.user_id)
        if advisor_id:
            # TODO: dispatch email sent event upon email sent succesfully
            await self._complete_task_by_type(
                case.case_id,
                TaskType.SEND_EMAIL,
                command.user_id,
            )
        else:
            logger.warning(
                f'Gamification: User {command.user_id} is not linked to an advisor profile. Skipping points reward for send email.',
            )

        await self.task_queue.enqueue(
            'run_dispatch_email_task',
            case_id=str(case.case_id),
            body=command.body,
            target_email=recipient_email,
        )

        # 4. Return recipient email for dispatching
        return recipient_email

    async def _resolve_advisor_id(self, user_id: UUID) -> UUID | None:
        """Resolve an advisor_id from a user_id."""
        advisor = await self.advisor_repo.find_by_user_id(user_id)
        return advisor.advisor_id if advisor else None
