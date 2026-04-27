"""API routes for Kanban Alert Dashboard management."""

import time
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from langgraph.graph.state import CompiledStateGraph
from pydantic import BaseModel, Field

from src.agents.state import AgentState
from src.api.lifecycle import get_agent, get_dbmanager
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
    """Schema for sending a finalized email."""

    body: str = Field(..., description='The finalized email content to send.')


@router.get('/', response_model=list[AlertStudent])
async def get_alerts(
    db_manager: Annotated[DatabaseManager, Depends(get_dbmanager)],
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
) -> dict[str, str]:
    """Update the Kanban state for a specific student's intervention."""
    valid_statuses = [
        'none',
        'new',
        'sent',
        'booked',
        'supporting',
        'resolved',
        'expired',
    ]
    if update.status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f'Invalid status. Must be one of {valid_statuses}',
        )

    try:
        db_manager.update_intervention_status(sid, update.status)
        logger.info(f'Updated student {sid} intervention status to {update.status}')
        return {'status': 'success', 'sid': sid, 'new_status': update.status}
    except Exception as e:
        logger.error(f'Failed to update status for student {sid}: {e}')
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get('/{sid}/draft', response_model=EmailDraft)
async def generate_email_draft(
    sid: str,
    agent: Annotated[
        CompiledStateGraph[AgentState, None, AgentState, AgentState],
        Depends(get_agent),
    ],
    db_manager: Annotated[DatabaseManager, Depends(get_dbmanager)],
) -> EmailDraft:
    """Generate a personalized, PII-safe email draft for a student."""
    # 1. Fetch student PII locally (never exposed to LLM)
    student_data = db_manager.execute(
        'sis_db',
        f"SELECT student_name, email FROM students WHERE sid = '{sid}'",
    )

    if not student_data or 'error' in student_data[0]:
        raise HTTPException(status_code=404, detail='Student not found.')

    student_name = student_data[0]['student_name']
    recipient_email = student_data[0]['email']

    # 2. Invoke Agent with anonymized request
    query = (
        f"Generate an empathetic nudge email draft for student sid '{sid}'. "
        'Use placeholders {{STUDENT_NAME}} and {{ADVISOR_LINK}}. '
        'Focus on their performance trajectory in the student_status_history.'
    )

    config = {'recursion_limit': 30, 'configurable': {'thread_id': str(uuid.uuid4())}}

    try:
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
            ai_response = last_message['content']

        # 3. Late-stage Interpolation
        personalized_body = ai_response.replace('{{STUDENT_NAME}}', student_name)
        # Default placeholder for link if not provided by some other config
        personalized_body = personalized_body.replace(
            '{{ADVISOR_LINK}}',
            'https://calendly.com/advisor-help',
        )

        return EmailDraft(
            sid=sid,
            recipient_email=recipient_email,
            subject='Checking in on your academic progress',
            body=personalized_body,
        )

    except Exception as e:
        logger.error(f'Failed to generate draft: {e}', exc_info=True)
        raise HTTPException(
            status_code=500, detail='Failed to generate AI draft.'
        ) from e


@router.post('/{sid}/send')
async def send_nudge_email(
    sid: str,
    request: SendEmailRequest,
    db_manager: Annotated[DatabaseManager, Depends(get_dbmanager)],
) -> dict[str, str]:
    """Dispatches the email and updates the intervention lifecycle."""
    # 1. Fetch student info for logging/dispatch
    student_data = db_manager.execute(
        'sis_db',
        f"SELECT student_name, email FROM students WHERE sid = '{sid}'",
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
            f"UPDATE students SET last_notified_timestamp = {time.time()} WHERE sid = '{sid}'",
        )
        return {'status': 'success', 'message': f'Email sent to {email}'}
    except Exception as e:
        logger.error(f'Failed to finalize send: {e}')
        raise HTTPException(status_code=500, detail=str(e)) from e
