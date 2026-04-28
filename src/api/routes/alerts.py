"""API routes for Kanban Alert Dashboard management."""

import time
import uuid
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from langgraph.graph.state import CompiledStateGraph
from pydantic import BaseModel, Field

from src.agents.state import AgentState
from src.api.auth import User, check_role
from src.api.lifecycle import get_agent, get_dbmanager, get_jobs_store
from src.api.models.response import (
    JobAcceptedResponse,
    JobStatusResponse,
)
from src.api.types import JobStore
from src.database.manager import DatabaseManager
from src.telemetry.logger import logger

router = APIRouter(prefix='/alerts', tags=['alerts'])


class AlertStudent(BaseModel):
    """Schema for a student in the Kanban alert dashboard."""

    sid: str = Field(..., description='Student identifier.')
    student_name: str = Field(..., description='Student name.')
    email: str = Field(..., description='Student email.')
    current_risk_status: str = Field(..., description='The type of anomaly detected.')
    intervention_status: str = Field(..., description='The current Kanban state.')


class StatusUpdate(BaseModel):
    """Schema for updating a student's intervention status."""

    status: str = Field(..., description='The new Kanban state.')


class EmailDraft(BaseModel):
    """Schema for a personalized email draft."""

    sid: str
    recipient_email: str
    subject: str
    body: str


class SendEmailRequest(BaseModel):
    """Schema for sending a personalized nudge email."""

    body: str = Field(..., description='The final email body to send.')


@router.get('/', response_model=list[AlertStudent])
async def get_alerts(
    db_manager: Annotated[DatabaseManager, Depends(get_dbmanager)],
    user: Annotated[User, Depends(check_role('advisor:read'))],
    status: str | None = Query(None),
) -> list[dict[str, str]]:
    """Retrieve students who have an active alert for the Kanban board."""
    sql: str = "SELECT sid, student_name, email, current_risk_status, intervention_status FROM students WHERE intervention_status != 'none'"
    if status:
        valid_statuses = ['new', 'sent', 'booked', 'supporting', 'resolved', 'expired']
        if status not in valid_statuses:
            raise HTTPException(
                status_code=400,
                detail=f'Invalid status filter. Must be one of {valid_statuses}',
            )
        sql += f" AND intervention_status = '{status}'"

    results = db_manager.execute('sis_db', sql)

    if results and 'error' in results[0]:
        logger.error(f'Error fetching alerts: {results[0]["error"]}')
        raise HTTPException(status_code=500, detail=results[0]['error'])

    return results


@router.patch('/{sid}/status')
async def update_alert_status(
    sid: str,
    update: StatusUpdate,
    db_manager: Annotated[DatabaseManager, Depends(get_dbmanager)],
    user: Annotated[User, Depends(check_role('advisor:write'))],
) -> dict[str, str]:
    """Manually transitions a student's Kanban state."""
    try:
        db_manager.update_intervention_status(sid, update.status)

        # Gamification hooks for status changes
        if update.status == 'booked':
            db_manager.inject_points(str(user.id), sid, 'meeting_booked')
        elif update.status == 'resolved':
            db_manager.inject_points(str(user.id), sid, 'student_resolved')

        return {'sid': sid, 'new_status': update.status}
    except Exception as e:
        logger.error(f'Failed to update status for student {sid}: {e}')
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post('/{sid}/draft/review')
async def review_draft(
    sid: str,
    db_manager: Annotated[DatabaseManager, Depends(get_dbmanager)],
    user: Annotated[User, Depends(check_role('advisor:write'))],
) -> dict[str, str]:
    """Explicitly rewards the advisor for reviewing the LLM draft."""
    try:
        db_manager.inject_points(str(user.id), sid, 'draft_reviewed')
        return {'status': 'success', 'message': 'Draft review points awarded.'}
    except Exception as e:
        logger.error(f'Failed to award draft review points for student {sid}: {e}')
        raise HTTPException(status_code=500, detail=str(e)) from e


async def _run_email_draft_task(
    job_id: str,
    sid: str,
    agent: CompiledStateGraph[AgentState, None, AgentState],
    db_manager: DatabaseManager,
    user: User,
    jobs: JobStore,
) -> None:
    """Encapsulates the email draft generation in a background task."""
    logger.set_context({'sid': sid, 'job_id': job_id})
    logger.info(f'API (BG): Generating email draft for student {sid}')

    try:
        # 1. Fetch student PII locally (never exposed to LLM)
        student_data = db_manager.execute(
            'sis_db',
            'SELECT student_name, email FROM students WHERE sid = ?',
            (sid,),
        )

        if not student_data or 'error' in student_data[0]:
            raise ValueError(f'Student {sid} not found.')

        student_name = student_data[0]['student_name']
        recipient_email = student_data[0]['email']

        # 2. Fetch performance data locally for anonymization
        perf_data = db_manager.execute(
            'sis_db',
            'SELECT academic_year, semester, baseline_avg, baseline_std, current_score_avg, z_score, anomaly_flag FROM student_status_history WHERE sid = ?',
            (sid,),
        )

        # 3. Create session-based anonymized_id
        anonymized_id = f'STU_{uuid.uuid4().hex[:8]}'

        # 4. Invoke Agent with anonymized request and local context
        query = (
            f"Generate an empathetic nudge email draft for student with anonymized_id '{anonymized_id}'. "
            f'Contextual Performance Patterns: {perf_data}. '
            'Use placeholders {{STUDENT_NAME}} and {{ADVISOR_LINK}}. '
            'Focus on their performance trajectory in the contextual data.'
        )

        config = {
            'recursion_limit': 30,
            'configurable': {
                'thread_id': str(uuid.uuid4()),
                'db_manager': db_manager,
                'user_role': user.role,
            },
        }

        final_state: AgentState | None = await agent.ainvoke(
            {'messages': [{'role': 'user', 'content': query}]},
            config=config,
        )

        if not final_state:
            raise ValueError('Agent returned an empty or invalid state.')

        messages = final_state.get('messages', [])
        ai_response = ''

        if messages:
            last_message = messages[-1]
            if hasattr(last_message, 'content'):
                ai_response = str(last_message.content)
            elif isinstance(last_message, dict) and 'content' in last_message:
                ai_response = str(last_message['content'])
            else:
                ai_response = str(last_message)

        # 3. Late-stage Interpolation
        personalized_body = ai_response.replace('{{STUDENT_NAME}}', student_name)
        # Default placeholder for link if not provided by some other config
        personalized_body = personalized_body.replace(
            '{{ADVISOR_LINK}}',
            'https://calendly.com/advisor-help',
        )

        # Update job status to completed
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
        logger.error(
            f'API (BG): Failed to generate draft for student {sid}: {e}', exc_info=True
        )
        jobs[job_id] = JobStatusResponse(
            job_id=job_id,
            status='failed',
            error=str(e),
        )
    finally:
        logger.clear_context()


@router.post('/{sid}/draft', response_model=JobAcceptedResponse, status_code=202)
async def generate_email_draft(
    sid: str,
    background_tasks: BackgroundTasks,
    agent: Annotated[
        CompiledStateGraph[AgentState, None, AgentState],
        Depends(get_agent),
    ],
    db_manager: Annotated[DatabaseManager, Depends(get_dbmanager)],
    user: Annotated[User, Depends(check_role('advisor:write'))],
    jobs: Annotated[JobStore, Depends(get_jobs_store)],
) -> JobAcceptedResponse:
    """Triggers the AI to generate a personalized email draft in the background.

    Returns a job_id immediately for status polling.
    """
    job_id = str(uuid.uuid4())

    # Initialize job status
    jobs[job_id] = JobStatusResponse(job_id=job_id, status='processing')

    # Schedule background task
    background_tasks.add_task(
        _run_email_draft_task,
        job_id=job_id,
        sid=sid,
        agent=agent,
        db_manager=db_manager,
        user=user,
        jobs=jobs,
    )

    return JobAcceptedResponse(job_id=job_id, status='processing')


@router.post('/{sid}/send')
async def send_nudge_email(
    sid: str,
    request: SendEmailRequest,
    db_manager: Annotated[DatabaseManager, Depends(get_dbmanager)],
    user: Annotated[User, Depends(check_role('advisor:write'))],
) -> dict[str, str]:
    """Dispatches the email and updates the intervention lifecycle."""
    # 1. Fetch student info for logging/dispatch
    student_data = db_manager.execute(
        'sis_db',
        'SELECT student_name, email FROM students WHERE sid = ?',
        (sid,),
    )

    if not student_data:
        raise HTTPException(status_code=404, detail='Student not found.')

    email = student_data[0]['email']

    # 2. Simulate email dispatch
    logger.info(f'DISPATCHING EMAIL to {email}: {request.body[:50]}...')

    # 3. Update Status
    try:
        db_manager.update_intervention_status(sid, 'sent')
        # Update last notified timestamp

        db_manager.execute(
            'sis_db',
            'UPDATE students SET last_notified_timestamp = ? WHERE sid = ?',
            (time.time(), sid),
            read_only=False,
        )

        # Gamification hook
        db_manager.inject_points(str(user.id), sid, 'email_sent')

        return {'status': 'success', 'message': f'Email sent to {email}'}
    except Exception as e:
        logger.error(f'Failed to finalize send: {e}')
        raise HTTPException(status_code=500, detail=str(e)) from e
