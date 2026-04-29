"""Service layer for Kanban Alert Dashboard management."""

import asyncio
import time
import uuid
from typing import TYPE_CHECKING, Any

from src.api.models.response import EmailDraft, JobStatusResponse
from src.baml_client.async_client import b as b_async
from src.telemetry.logger import logger
from src.utils.env import getenv

if TYPE_CHECKING:
    from src.api.services.gamification import GamificationService
    from src.api.types import JobStore
    from src.database.manager import DatabaseManager
    from src.database.repositories.student_repository import StudentRepository


class AlertService:
    """Service for managing student alerts and interventions."""

    def __init__(
        self,
        db_manager: 'DatabaseManager',
        gamification_service: 'GamificationService',
        student_repo: 'StudentRepository',
    ) -> None:
        """Initialize the AlertService with dependencies.

        Args:
            db_manager: The database manager instance.
            gamification_service: Service for awarding points.
            student_repo: Repository for student operations.
        """
        self.db = db_manager
        self.gamification_service = gamification_service
        self.student_repo = student_repo
        # Limit concurrency of AI draft generation
        self._semaphore = asyncio.Semaphore(int(getenv('MAX_CONCURRENT_DRAFTS', '5')))

    async def get_alerts(self, status_filter: str | None = None) -> list[dict[str, Any]]:
        """Retrieve students who have an active alert for the Kanban board."""
        sql = (
            "SELECT s.sid, s.student_name, s.email, s.current_risk_status, s.intervention_status, s.draft_job_id, "
            "e.subject as draft_subject, e.body as draft_body "
            "FROM students s "
            "LEFT JOIN ("
            "  SELECT sid, subject, body, ROW_NUMBER() OVER (PARTITION BY sid ORDER BY created_at DESC) as rn "
            "  FROM intervention_emails WHERE status = 'draft'"
            ") e ON s.sid = e.sid AND e.rn = 1 "
            "WHERE s.intervention_status != 'none'"
        )
        params: list[Any] = []

        if status_filter:
            sql += ' AND s.intervention_status = ?'
            params.append(status_filter)

        results = await self.db.execute_async('sis_db', sql, tuple(params))

        if results and isinstance(results[0], dict) and 'error' in results[0]:
            raise ValueError(f"Database error: {results[0]['error']}")

        return results

    async def update_status(self, sid: str, status: str, user_id: str) -> None:
        """Update a student's intervention status and record gamification points."""
        await self.student_repo.update_intervention_status(sid, status)

        # Gamification hooks for status changes
        if status == 'booked':
            await self.gamification_service.award_points(user_id, sid, 'meeting_booked')
        elif status == 'resolved':
            await self.gamification_service.award_points(user_id, sid, 'student_resolved')

    async def award_review_points(self, sid: str, user_id: str) -> None:
        """Award points for reviewing an LLM draft."""
        await self.gamification_service.award_points(user_id, sid, 'draft_reviewed')

    async def trigger_draft(
        self,
        sid: str,
        arq_pool: Any,
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
        if update_db:
            await self.db.execute_async(
                'sis_db',
                'UPDATE students SET draft_job_id = ? WHERE sid = ?',
                (job_id, sid),
                read_only=False,
            )

        # Enqueue ARQ job
        await arq_pool.enqueue_job(
            'run_email_draft_task',
            job_id=job_id,
            sid=sid,
            jobs=jobs,
            booking_link=booking_link,
            user_id=user_id,
        )

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
                # 1. Fetch student PII - unblocked
                student_data = await self.student_repo.get_student_pii(sid)

                if not student_data:
                    raise ValueError(f'Student {sid} not found.')

                student_name = student_data['student_name']
                recipient_email = student_data['email']

                # 2. Fetch performance data - unblocked
                perf_raw = await self.db.execute_async(
                    'sis_db',
                    'SELECT academic_year as yr, semester as sem, week as wk, '
                    'current_score_avg as score, anomaly_flag as status FROM student_status_history '
                    'WHERE sid = ? ORDER BY academic_year DESC, semester DESC, week DESC '
                    'LIMIT 4',
                    (sid,),
                )

                # 3. Format context string
                history_lines = []
                for p in perf_raw:
                    history_lines.append(f"Year {p['yr']} Sem {p['sem']} Week {p['wk']}: Score {p['score']} ({p['status']})")
                context_str = "Trend: " + " | ".join(history_lines)

                # 4. Invoke BAML (Already async)
                user_intent = (
                    'Generate a short, supportive email to a student whose grades have dropped. '
                    'Mention their recent performance trend and offer a meeting.'
                )
                ai_response = await b_async.GenerateDraftEmail(user_intent, context_str)

                # 5. Interpolation
                personalized_body = ai_response.replace('{{STUDENT_NAME}}', student_name)
                link_to_use = booking_link or 'https://calendly.com/advisor-help'
                personalized_body = personalized_body.replace('{{ADVISOR_LINK}}', link_to_use)

                draft = EmailDraft(
                    sid=sid,
                    recipient_email=recipient_email,
                    subject='Checking in on your academic progress',
                    body=personalized_body,
                )

                # 6. Persistent storage for the draft - unblocked
                email_id = str(uuid.uuid4())
                await self.db.execute_async(
                    'sis_db',
                    'INSERT INTO intervention_emails (email_id, sid, advisor_id, subject, body, status) VALUES (?, ?, ?, ?, ?, ?)',
                    (email_id, sid, user_id, draft.subject, draft.body, 'draft'),
                    read_only=False,
                )

                # 7. Clear the job tracker - unblocked
                await self.db.execute_async(
                    'sis_db',
                    'UPDATE students SET draft_job_id = NULL WHERE sid = ?',
                    (sid,),
                    read_only=False,
                )

                jobs[job_id] = JobStatusResponse(
                    job_id=job_id,
                    status='completed',
                    result=draft,
                )

            except Exception as e:
                logger.error(f'AlertService: Failed to generate draft: {e}', exc_info=True)
                jobs[job_id] = JobStatusResponse(job_id=job_id, status='failed', error=str(e))
            finally:
                logger.clear_context()

    async def send_email(self, sid: str, body: str, user_id: str) -> str:
        """Dispatch a nudge email and update state."""
        student_data = await self.student_repo.get_student_pii(sid)

        if not student_data:
            raise ValueError(f'Student {sid} not found.')

        email = student_data['email']
        logger.info(f'DISPATCHING EMAIL to {email}: {body[:50]}...')

        await self.student_repo.update_intervention_status(sid, 'sent')

        # Update or Insert into intervention_emails as 'sent'
        await self.db.execute_async(
            'sis_db',
            """
            UPDATE intervention_emails
            SET status = 'sent', sent_at = CURRENT_TIMESTAMP, body = ?
            WHERE email_id = (
                SELECT email_id FROM intervention_emails
                WHERE sid = ? AND status = 'draft'
                ORDER BY created_at DESC LIMIT 1
            )
            """,
            (body, sid),
            read_only=False,
        )

        await self.db.execute_async(
            'sis_db',
            'UPDATE students SET last_notified_timestamp = ? WHERE sid = ?',
            (time.time(), sid),
            read_only=False,
        )

        # Gamification
        await self.gamification_service.award_points(user_id, sid, 'email_sent')

        return email

    async def get_email_history(self, sid: str) -> list[dict[str, Any]]:
        """Retrieve communication history for a student."""
        sql = """
            SELECT email_id, subject, body, status, created_at, sent_at
            FROM intervention_emails
            WHERE sid = ?
            ORDER BY created_at DESC
        """
        return await self.db.execute_async('sis_db', sql, (sid,))
