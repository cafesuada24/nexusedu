"""Service layer for Kanban Alert Dashboard management."""

import asyncio
import time
import uuid
from typing import TYPE_CHECKING, Any

from fastapi import BackgroundTasks
from src.api.models.response import EmailDraft, JobStatusResponse
from src.baml_client.async_client import b as b_async
from src.telemetry.logger import logger
from src.utils.env import getenv

if TYPE_CHECKING:
    from src.api.types import JobStore
    from src.database.manager import DatabaseManager


class AlertService:
    """Service for managing student alerts and interventions."""

    def __init__(self, db_manager: 'DatabaseManager') -> None:
        """Initialize the AlertService with a DatabaseManager.

        Args:
            db_manager: The database manager instance.
        """
        self.db = db_manager
        # Limit concurrency of AI draft generation
        self._semaphore = asyncio.Semaphore(int(getenv('MAX_CONCURRENT_DRAFTS', '2')))

    # ... (get_alerts, update_status, award_review_points, trigger_draft remain same)


    def get_alerts(self, status_filter: str | None = None) -> list[dict[str, Any]]:
        """Retrieve students who have an active alert for the Kanban board.

        Args:
            status_filter: Optional Kanban status to filter by.

        Returns:
            List of student alert records.

        Raises:
            ValueError: If the database returns an error.
        """
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

        results = self.db.execute('sis_db', sql, tuple(params))

        if results and isinstance(results[0], dict) and 'error' in results[0]:
            raise ValueError(f"Database error: {results[0]['error']}")

        return results

    def update_status(self, sid: str, status: str, user_id: str) -> None:
        """Update a student's intervention status and record gamification points.

        Args:
            sid: Student identifier.
            status: New Kanban status.
            user_id: The ID of the advisor performing the update.
        """
        self.db.update_intervention_status(sid, status)

        # Gamification hooks for status changes
        if status == 'booked':
            self.db.inject_points(user_id, sid, 'meeting_booked')
        elif status == 'resolved':
            self.db.inject_points(user_id, sid, 'student_resolved')

    def award_review_points(self, sid: str, user_id: str) -> None:
        """Award points for reviewing an LLM draft.

        Args:
            sid: Student identifier.
            user_id: The ID of the advisor.
        """
        self.db.inject_points(user_id, sid, 'draft_reviewed')

    def trigger_draft(
        self,
        sid: str,
        background_tasks: 'BackgroundTasks',
        jobs: 'JobStore',
        user_id: str | None = None,
        booking_link: str | None = None,
        update_db: bool = True,
    ) -> str:
        """Trigger a background draft generation and update the database.

        Args:
            sid: Student identifier.
            background_tasks: FastAPI background tasks.
            jobs: Job storage dictionary.
            user_id: ID of the user requesting the draft.
            booking_link: Custom booking link.
            update_db: Whether to update the student record in DB immediately.

        Returns:
            The generated job_id.
        """
        job_id = str(uuid.uuid4())

        # Initialize job status
        jobs[job_id] = JobStatusResponse(job_id=job_id, status='processing')

        # Update database with the job_id if not batching
        if update_db:
            self.db.execute(
                'sis_db',
                'UPDATE students SET draft_job_id = ? WHERE sid = ?',
                (job_id, sid),
                read_only=False,
            )

        # Schedule background task
        background_tasks.add_task(
            self.run_email_draft_task,
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
        """Generate a personalized email draft in the background.

        Args:
            job_id: Unique job identifier.
            sid: Student identifier.
            jobs: Job storage dictionary.
            booking_link: Custom booking link.
            user_id: ID of the user requesting the draft.
        """
        async with self._semaphore:
            logger.set_context({'sid': sid, 'job_id': job_id})
            logger.info(
                f'AlertService: Generating email draft for student {sid}',
            )

            try:
                # 1. Fetch student PII - run in thread to not block event loop
                student_data = await asyncio.to_thread(
                    self.db.execute,
                    'sis_db',
                    'SELECT student_name, email FROM students WHERE sid = ?',
                    (sid,),
                )

                if not student_data or 'error' in student_data[0]:
                    raise ValueError(f'Student {sid} not found.')

                student_name = student_data[0]['student_name']
                recipient_email = student_data[0]['email']

                # 2. Fetch performance data (Optimized: limit to last 4 weeks)
                perf_raw = await asyncio.to_thread(
                    self.db.execute,
                    'sis_db',
                    'SELECT academic_year as yr, semester as sem, week as wk, '
                    'current_score_avg as score, anomaly_flag as status FROM student_status_history '
                    'WHERE sid = ? ORDER BY academic_year DESC, semester DESC, week DESC '
                    'LIMIT 4',
                    (sid,),
                )

                # 3. Format context string to be more LLM-friendly and compact
                # Reducing numeric noise (baseline_avg, z_score) and focusing on the trend
                history_lines = []
                for p in perf_raw:
                    history_lines.append(f"Year {p['yr']} Sem {p['sem']} Week {p['wk']}: Score {p['score']} ({p['status']})")
                context_str = "Trend: " + " | ".join(history_lines)

                # 4. Invoke BAML
                user_intent = (
                    'Generate a short, supportive email to a student whose grades have dropped. '
                    'Mention their recent performance trend and offer a meeting.'
                )
                ai_response = await b_async.GenerateDraftEmail(user_intent, context_str)

                # 5. Interpolation
                personalized_body = ai_response.replace('{{STUDENT_NAME}}', student_name)
                link_to_use = booking_link or 'https://calendly.com/advisor-help'
                personalized_body = personalized_body.replace(
                    '{{ADVISOR_LINK}}',
                    link_to_use,
                )

                draft = EmailDraft(
                    sid=sid,
                    recipient_email=recipient_email,
                    subject='Checking in on your academic progress',
                    body=personalized_body,
                )

                # 6. Persistent storage for the draft - run in thread
                email_id = str(uuid.uuid4())
                await asyncio.to_thread(
                    self.db.execute,
                    'sis_db',
                    'INSERT INTO intervention_emails (email_id, sid, advisor_id, subject, body, status) VALUES (?, ?, ?, ?, ?, ?)',
                    (email_id, sid, user_id, draft.subject, draft.body, 'draft'),
                    read_only=False,
                )

                # 7. Clear the job tracker - run in thread
                await asyncio.to_thread(
                    self.db.execute,
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
    def send_email(self, sid: str, body: str, user_id: str) -> str:
        """Dispatch a nudge email and update state.

        Args:
            sid: Student identifier.
            body: Email body content.
            user_id: ID of the advisor sending the email.

        Returns:
            Recipient email address.

        Raises:
            ValueError: If student not found.
        """
        student_data = self.db.execute(
            'sis_db',
            'SELECT student_name, email FROM students WHERE sid = ?',
            (sid,),
        )

        if not student_data:
            raise ValueError(f'Student {sid} not found.')

        email = student_data[0]['email']
        logger.info(f'DISPATCHING EMAIL to {email}: {body[:50]}...')

        self.db.update_intervention_status(sid, 'sent')
        
        # Update or Insert into intervention_emails as 'sent'
        # We look for the latest draft for this student and advisor
        self.db.execute(
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

        self.db.execute(
            'sis_db',
            'UPDATE students SET last_notified_timestamp = ? WHERE sid = ?',
            (time.time(), sid),
            read_only=False,
        )

        # Gamification
        self.db.inject_points(user_id, sid, 'email_sent')

        return email

    def get_email_history(self, sid: str) -> list[dict[str, Any]]:
        """Retrieve communication history for a student.

        Args:
            sid: Student identifier.

        Returns:
            List of sent or drafted emails.
        """
        sql = """
            SELECT email_id, subject, body, status, created_at, sent_at
            FROM intervention_emails
            WHERE sid = ?
            ORDER BY created_at DESC
        """
        return self.db.execute('sis_db', sql, (sid,))
