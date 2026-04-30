"""Base exceptions for the application layer."""

class ApplicationError(Exception):
    """Base class for all application-related errors."""
    pass

class UseCaseError(ApplicationError):
    """Raised when a specific use case fails due to business rule violations."""
    pass

class AuthenticationError(ApplicationError):
    """Raised when authentication fails at the application level."""
    pass
