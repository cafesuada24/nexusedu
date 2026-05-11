from dataclasses import dataclass, field
from datetime import datetime

from src.core.identifiers import EntityID, generate_uuid


@dataclass(frozen=True)
class PointLedgerEntry:
    """A single entry in the point ledger."""
    id: EntityID
    advisor_id: EntityID
    case_id: EntityID
    action: str
    points: int
    earned_at: datetime

@dataclass
class PointLedger:
    """Aggregate root for an advisor's point ledger."""
    advisor_id: EntityID
    entries: list[PointLedgerEntry] = field(default_factory=list[PointLedgerEntry])
    _pending_entries: list[PointLedgerEntry] = field(default_factory=list[PointLedgerEntry], init=False)

    def award_points(
        self,
        case_id: EntityID,
        action: str,
        points: int,
        earned_at: datetime,
    ) -> None:
        """Adds a new point award to the ledger."""
        if points <= 0:
            raise ValueError("Points must be positive.")

        entry = PointLedgerEntry(
            id=generate_uuid(),
            advisor_id=self.advisor_id,
            case_id=case_id,
            action=action,
            points=points,
            earned_at=earned_at,
        )
        self._pending_entries.append(entry)
        self.entries.append(entry)

    def get_pending_entries(self) -> list[PointLedgerEntry]:
        """Returns the list of entries that haven't been persisted yet."""
        return list(self._pending_entries)

    def clear_pending_entries(self) -> None:
        """Clears the list of pending entries after successful persistence."""
        self._pending_entries.clear()
