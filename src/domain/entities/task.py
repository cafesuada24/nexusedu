"""Task domain entity."""

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from src.domain.value_objects.status import TaskStatus, TaskType


@dataclass
class Task:
    """Represents a specific task associated with an intervention case."""

    task_id: UUID = field(default_factory=uuid4)
    case_id: UUID = field(default_factory=uuid4)
    action_type: TaskType = TaskType.SEND_EMAIL
    status: TaskStatus = TaskStatus.PENDING
    points_reward: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime | None = None
    completed_by_advisor_id: UUID | None = None
