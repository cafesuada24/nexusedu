"""Advisor domain entity."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Advisor:
    """Represents an academic advisor."""

    advisor_id: str
    name: Optional[str] = None
    email: Optional[str] = None
