"""API routes for Kanban Alert Dashboard management.
"""

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from src.telemetry.logger import logger
from src.tools.db import db_manager

router = APIRouter(prefix="/alerts", tags=["alerts"])

class AlertStudent(BaseModel):
    """Schema for a student in the Kanban alert dashboard."""
    sid: str = Field(..., description="Student identifier.")
    student_name: str = Field(..., description="Student name.")
    email: str = Field(..., description="Student email.")
    current_risk_status: str = Field(..., description="The type of anomaly detected.")
    intervention_status: str = Field(..., description="The current Kanban state.")

class StatusUpdate(BaseModel):
    """Schema for updating a student's intervention status."""
    status: str = Field(..., description="The new Kanban state.")

@router.get("/", response_model=List[AlertStudent])
async def get_alerts(status: Optional[str] = Query(None)) -> list:
    """Retrieve students who have an active alert for the Kanban board.
    
    Args:
        status: Optional filter for a specific Kanban state.
        
    Returns:
        A list of students with active interventions.
    """
    sql = "SELECT sid, student_name, email, current_risk_status, intervention_status FROM students WHERE intervention_status != 'none'"
    if status:
        # Use parameterized query equivalent or safe concatenation since it's a fixed list check
        valid_statuses = ['new', 'sent', 'booked', 'supporting', 'resolved', 'expired']
        if status not in valid_statuses:
            raise HTTPException(status_code=400, detail=f"Invalid status filter. Must be one of {valid_statuses}")
        sql += f" AND intervention_status = '{status}'"
    
    results = db_manager.execute('sis_db', sql)
    
    if results and isinstance(results[0], dict) and 'error' in results[0]:
        logger.error(f"Error fetching alerts: {results[0]['error']}")
        raise HTTPException(status_code=500, detail=results[0]['error'])
        
    return results

@router.patch("/{sid}/status")
async def update_alert_status(sid: str, update: StatusUpdate) -> dict:
    """Update the Kanban state for a specific student's intervention.
    
    Args:
        sid: Student identifier.
        update: The new status to apply.
        
    Returns:
        Confirmation of the update.
    """
    valid_statuses = ['none', 'new', 'sent', 'booked', 'supporting', 'resolved', 'expired']
    if update.status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of {valid_statuses}")
    
    try:
        db_manager.update_intervention_status(sid, update.status)
        logger.info(f"Updated student {sid} intervention status to {update.status}")
        return {"status": "success", "sid": sid, "new_status": update.status}
    except Exception as e:
        logger.error(f"Failed to update status for student {sid}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
