"""Advisor domain entity."""

from dataclasses import dataclass
from uuid import UUID


@dataclass
class Advisor:
    """Represents an academic advisor."""

    advisor_id: UUID
    name: str
    email: str
    title: str | None = None
    phone: str | None = None
    faculty: str | None = None
    office: str | None = None
    bio: str | None = None
