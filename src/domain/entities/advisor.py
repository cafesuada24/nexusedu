"""Advisor domain entity."""

from dataclasses import dataclass

from src.core.identifiers import EntityID


@dataclass
class Advisor:
    """Represents an academic advisor."""

    advisor_id: EntityID
    user_id: EntityID | None
    name: str
    email: str
    title: str | None = None
    phone: str | None = None
    faculty: str | None = None
    office: str | None = None
    bio: str | None = None
