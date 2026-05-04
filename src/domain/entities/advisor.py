"""Advisor domain entity."""

from dataclasses import dataclass
from uuid import UUID


@dataclass
class Advisor:
    """Represents an academic advisor."""

    advisor_id: UUID
    name: str
    email: str
    user_id: UUID | None = None
