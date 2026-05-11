"""Idempotency repository interface."""

from typing import Protocol

from src.core.identifiers import EntityID


class IdempotencyRepository(Protocol):
    """Interface for idempotency key management."""

    async def check_key(self, key: EntityID) -> bool:
        """Check if an idempotency key exists."""
        ...

    async def record_key(self, key: EntityID) -> None:
        """Record a new idempotency key."""
        ...
