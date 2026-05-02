"""Case domain entity."""

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from src.domain.value_objects.status import CaseStatus


@dataclass
class Case:
    """Represents an intervention case for a student."""

    case_id: UUID = field(default_factory=uuid4)
    sid: UUID = field(default_factory=uuid4)
    status: CaseStatus = CaseStatus.OPEN
    created_at: datetime = field(default_factory=datetime.now)
    resolved_at: datetime | None = None
    assigned_advisor_id: UUID | None = None
