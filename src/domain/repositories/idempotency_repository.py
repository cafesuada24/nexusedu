"""Idempotency repository interface."""

from typing import Protocol
from uuid import UUID


class IdempotencyRepository(Protocol):
    """Interface for idempotency key management."""

    async def check_key(self, key: UUID) -> bool:
        """Check if an idempotency key exists."""
        ...

    async def record_key(self, key: UUID) -> None:
        """Record a new idempotency key."""
        ...
