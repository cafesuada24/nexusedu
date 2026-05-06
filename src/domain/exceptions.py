"""Base exceptions for the domain layer."""

from uuid import UUID


_NOT_FOUND_MESSAGE_TEMPLATE = '{entity} with ID {id} not found.'


class DomainError(Exception):
    """Base class for all domain-related errors."""

    pass


# ==========================
# ========== CASE ==========
# ==========================


class CaseError(DomainError):
    """Base error for Case."""


class CaseAlreadyAssignedError(CaseError):
    """Raised when a case is already assigned."""

    def __init__(self, case_id: UUID) -> None:
        super().__init__(f'Case with id {case_id} is already assigned.')


class CaseNotFoundError(CaseError):
    """Raised when a case is not found."""

    def __init__(self, case_id: UUID):
        super().__init__(
            _NOT_FOUND_MESSAGE_TEMPLATE.format(
                entity='Case',
                id=case_id,
            ),
        )


# =============================
# ========== Advisor ==========
# =============================


class AdvisorError(DomainError):
    """Base error for Advisor."""


class AdvisorNotFoundError(AdvisorError):
    """Raised when a requested advisor not found."""

    def __init__(self, advisor_id: UUID):
        super().__init__(
            _NOT_FOUND_MESSAGE_TEMPLATE.format(
                entity='Advisor',
                id=advisor_id,
            ),
        )


class ValidationError(DomainError):
    """Raised when a domain invariant is violated."""

    pass


class UnauthorizedError(DomainError):
    """Raised when an operation is not permitted in the domain."""

    pass
