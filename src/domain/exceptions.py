"""Base exceptions for the domain layer."""

from uuid import UUID


class DomainError(Exception):
    """Base class for all domain-related errors."""

    pass


class CaseAlreadyAssignedError(DomainError):
    """Raised when a case is already assigned."""

    def __init__(self, case_id: UUID) -> None:
        super().__init__(f'Case with id {case_id} is already assigned.')


class EntityNotFoundError(DomainError):
    """Raised when a requested entity is not found."""

    def __init__(self, entity_name: str, entity_id: str):
        self.entity_name = entity_name
        self.entity_id = entity_id
        super().__init__(f'{entity_name} with id {entity_id} was not found.')


class ValidationError(DomainError):
    """Raised when a domain invariant is violated."""

    pass


class UnauthorizedError(DomainError):
    """Raised when an operation is not permitted in the domain."""

    pass
