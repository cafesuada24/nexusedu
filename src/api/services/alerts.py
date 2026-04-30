"""Service layer for Kanban Alert Dashboard management."""

import asyncio
import uuid
from typing import TYPE_CHECKING, Any

from arq import ArqRedis

from src.api.models.response import EmailDraft, JobStatusResponse
from src.baml_client.async_client import b as b_async
from src.domain.ports.repositories import (
    AlertRepository,
    EmailRepository,
    IdempotencyRepository,
    StudentRepository,
)
from src.telemetry.logger import logger
from src.utils.env import getenv

if TYPE_CHECKING:
    from src.api.services.gamification import GamificationService
    from src.api.types import JobStore


class AlertService:
    """Service for managing student alerts and interventions."""

    def __init__(
        self,
        alert_repo: AlertRepository,
        email_repo: EmailRepository,
        student_repo: StudentRepository,
        idempotency_repo: IdempotencyRepository,
        gamification_service: 'GamificationService',
    ) -> None:
        """Initialize the AlertService with dependencies.

        Args:
            alert_repo: Repository for alert operations.
            email_repo: Repository for email operations.
            student_repo: Repository for student operations.
            idempotency_repo: Repository for idempotency management.
            gamification_service: Service for awarding points.
        """
        self.alert_repo = alert_repo
        self.email_repo = email_repo
        self.student_repo = student_repo
        self.idempotency_repo = idempotency_repo
        self.gamification_service = gamification_service
        # Limit concurrency of AI draft generation
        self._semaphore = asyncio.Semaphore(int(getenv('MAX_CONCURRENT_DRAFTS', '5')))

    async def get_alerts(
        self, status_filter: str | None = None
    ) -> list[dict[str, Any]]:
        """Retrieve students who have an active alert for the Kanban board."""
        return await self.alert_repo.get_active_alerts(status_filter)

    async def update_status(self, sid: str, status: str, user_id: str) -> None:
        """Update a student's intervention status and record gamification points."""
        await self.student_repo.update_intervention_status(sid, status)

        # Gamification hooks for status changes
        if status == 'booked':
            await self.gamification_service.award_points(user_id, sid, 'meeting_booked')
        elif status == 'resolved':
            await self.gamification_service.award_points(
                user_id, sid, 'student_resolved'
            )

    async def award_review_points(self, sid: str, user_id: str) -> None:
        """Award points for reviewing an LLM draft."""
        await self.gamification_service.award_points(user_id, sid, 'draft_reviewed')

    async def trigger_draft(
        self,
        sid: str,
        arq_pool: ArqRedis | None,
        jobs: 'JobStore',
        user_id: str | None = None,
        booking_link: str | None = None,
        update_db: bool = True,
    ) -> str:
        """Trigger a background draft generation and update the database."""
        job_id = str(uuid.uuid4())

        # Initialize job status
        jobs[job_id] = JobStatusResponse(job_id=job_id, status='processing')

        # Update database with the job_id if not batching

        # Enqueue ARQ job
        if arq_pool:
            if update_db:
                await self.student_repo.update_draft_job_id(sid, job_id)
            await arq_pool.enqueue_job(
                'run_email_draft_task',
                job_id=job_id,
                sid=sid,
                jobs=jobs,
                booking_link=booking_link,
                user_id=user_id,
            )
        else:
            logger.warning(
                'AlertService: ARQ Pool not available. Skipping background task.',
            )
            jobs[job_id].status = 'failed'
            jobs[job_id].error = 'Background processing unavailable (Redis down).'

        return job_id

    async def run_email_draft_task(
        self,
        job_id: str,
        sid: str,
        jobs: 'JobStore',
        booking_link: str | None = None,
        user_id: str | None = None,
    ) -> None:
        """Generate a personalized email draft in the background."""
        async with self._semaphore:
            logger.set_context({'sid': sid, 'job_id': job_id})
            logger.info(f'AlertService: Generating email draft for student {sid}')

            try:
                # 1. Fetch student PII
                student_data = await self.student_repo.get_pii(sid)

                if not student_data:
                    raise ValueError(f'Student {sid} not found.')

                student_name = student_data['student_name']
                recipient_email = student_data['email']

                # 2. Fetch performance data
                perf_raw = await self.student_repo.get_recent_performance(sid)

                # 3. Format context string
                history_lines = []
                for p in perf_raw:
                    history_lines.append(
                        f'Year {p["yr"]} Sem {p["sem"]} Week {p["wk"]}: Score {p["score"]} ({p["status"]})'
                    )
                context_str = 'Trend: ' + ' | '.join(history_lines)

                # 4. Invoke BAML (Already async)
                user_intent = (
                    'Generate a short, supportive email to a student whose grades have dropped. '
                    'Mention their recent performance trend and offer a meeting.'
                )
                ai_response = await b_async.GenerateDraftEmail(user_intent, context_str)

                # 5. Interpolation
                personalized_body = ai_response.replace(
                    '{{STUDENT_NAME}}', student_name
                )
                link_to_use = booking_link or 'https://calendly.com/advisor-help'
                personalized_body = personalized_body.replace(
                    '{{ADVISOR_LINK}}', link_to_use
                )

                draft = EmailDraft(
                    sid=sid,
                    recipient_email=recipient_email,
                    subject='Checking in on your academic progress',
                    body=personalized_body,
                )

                # 6. Persistent storage for the draft
                await self.email_repo.create_draft(
                    sid, user_id, draft.subject, draft.body
                )

                # 7. Clear the job tracker
                await self.student_repo.update_draft_job_id(sid, None)

                jobs[job_id] = JobStatusResponse(
                    job_id=job_id,
                    status='completed',
                    result=draft,
                )

            except Exception as e:
                logger.error(
                    f'AlertService: Failed to generate draft: {e}', exc_info=True
                )
                jobs[job_id] = JobStatusResponse(
                    job_id=job_id, status='failed', error=str(e)
                )
            finally:
                logger.clear_context()

    async def send_email(self, sid: str, body: str, user_id: str) -> str:
        """Dispatch a nudge email and update state."""
        student_data = await self.student_repo.get_pii(sid)

        if not student_data:
            raise ValueError(f'Student {sid} not found.')

        email = student_data['email']
        logger.info(f'DISPATCHING EMAIL to {email}: {body[:50]}...')

        await self.student_repo.update_intervention_status(sid, 'sent')

        # Update or Insert into intervention_emails as 'sent'
        await self.email_repo.mark_as_sent(sid, body)

        await self.student_repo.update_last_notified(sid)

        # Gamification
        await self.gamification_service.award_points(user_id, sid, 'email_sent')

        return email

    async def get_email_history(self, sid: str) -> list[dict[str, Any]]:
        """Retrieve communication history for a student."""
        return await self.email_repo.get_history(sid)

    async def check_idempotency(self, key: str) -> bool:
        """Check if an idempotency key has been used."""
        return await self.idempotency_repo.check_key(key)

    async def record_idempotency(self, key: str) -> None:
        """Record a new idempotency key."""
        await self.idempotency_repo.record_key(key)

    async def get_draft_status(self, sid: str) -> bool:
        """Check if a student has an active draft generation job."""
        student = await self.student_repo.get_by_id(sid)
        return bool(student and student.draft_job_id)
