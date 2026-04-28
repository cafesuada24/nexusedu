"""Service layer for Kanban Alert Dashboard management."""

import time
from typing import TYPE_CHECKING, Any

from src.api.models.response import EmailDraft, JobStatusResponse
from src.baml_client.async_client import b as b_async
from src.telemetry.logger import logger

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
            "SELECT sid, student_name, email, current_risk_status, intervention_status "
            "FROM students WHERE intervention_status != 'none'"
        )
        params: list[Any] = []

        if status_filter:
            sql += ' AND intervention_status = ?'
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
        logger.set_context({'sid': sid, 'job_id': job_id})
        logger.info(
            f'AlertService: Generating email draft for student {sid} (requested by {user_id})',
        )

        try:
            # 1. Fetch student PII
            student_data = self.db.execute(
                'sis_db',
                'SELECT student_name, email FROM students WHERE sid = ?',
                (sid,),
            )

            if not student_data or 'error' in student_data[0]:
                raise ValueError(f'Student {sid} not found.')

            student_name = student_data[0]['student_name']
            recipient_email = student_data[0]['email']

            # 2. Fetch performance data
            perf_data = self.db.execute(
                'sis_db',
                'SELECT academic_year, semester, week, baseline_avg, baseline_std, '
                'current_score_avg, z_score, anomaly_flag FROM student_status_history '
                'WHERE sid = ? ORDER BY academic_year DESC, semester DESC, week DESC',
                (sid,),
            )

            # 3. Invoke BAML
            user_intent = (
                'Generate a supportive nudge email draft based on performance history. '
                'Highlight changes and offer assistance.'
            )
            context_str = f'Student Performance History: {perf_data}'
            ai_response = await b_async.GenerateDraftEmail(user_intent, context_str)

            # 4. Interpolation
            personalized_body = ai_response.replace('{{STUDENT_NAME}}', student_name)
            link_to_use = booking_link or 'https://calendly.com/advisor-help'
            personalized_body = personalized_body.replace(
                '{{ADVISOR_LINK}}',
                link_to_use,
            )

            # Update job status
            jobs[job_id] = JobStatusResponse(
                job_id=job_id,
                status='completed',
                result=EmailDraft(
                    sid=sid,
                    recipient_email=recipient_email,
                    subject='Checking in on your academic progress',
                    body=personalized_body,
                ),
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
        self.db.execute(
            'sis_db',
            'UPDATE students SET last_notified_timestamp = ? WHERE sid = ?',
            (time.time(), sid),
            read_only=False,
        )

        # Gamification
        self.db.inject_points(user_id, sid, 'email_sent')

        return email
