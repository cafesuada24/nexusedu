"""Base exceptions for the application layer."""

from uuid import UUID


class ApplicationError(Exception):
    """Base class for all application-related errors."""

    pass


class EntityNotFoundError(ApplicationError):
    """Base class for 'Not Found' scenarios."""

    def __init__(self, entity_name: str, entity_id: object) -> None:
        self.entity_name = entity_name
        self.entity_id = entity_id
        super().__init__(f"{entity_name} with ID '{entity_id}' was not found.")


class InvalidStatusTransitionError(ApplicationError):
    """Raised when an invalid transition happen."""


class ConcurrencyError(ApplicationError):
    """Raised when a concurrency bad condition happen."""


# ==============================================
# ================= ADVISOR ====================
# ==============================================

class AdvisorError(ApplicationError):
    """Raised when an error related to advisor occured."""

class AdvisorProfileNotLinkedError(ApplicationError):
    """Raised when an advisor account not linked to an advisor profile."""

    def __init__(self, user_id: UUID) -> None:
        super().__init__(f"account with ID '{user_id}' does not link to any advisor profile.")


class AuthenticationError(ApplicationError):
    """Raised when authentication fails at the application level."""

    pass
