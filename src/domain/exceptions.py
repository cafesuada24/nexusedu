"""Base exceptions for the domain layer."""

from datetime import datetime
from uuid import UUID

_NOT_FOUND_MESSAGE_TEMPLATE = '{entity} with ID {id} not found.'


class DomainError(Exception):
    """Base class for all domain-related errors."""

    pass

class InvalidActionError(Exception):
    """Raised when an user trying to perform an invalid action."""


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

class InvalidStateTransitionError(CaseError):
    """Raised when an invalid state transition happened."""

    def __init__(self, current_status: str, attempted_action: str):
        self.message = f"Cannot transite to {attempted_action} because the current status is {current_status}."
        super().__init__(self.message)

class CaseNotYetAcceptedError(CaseError):
    def __init__(self, case_id: UUID):
        super().__init__(f"Action denied: Case {case_id} must be accepted first.")

class CaseAlreadyClosedError(CaseError):
    """Raised when an advisor trying to work on an unavailable case."""

    def __init__(self, case_id: UUID) -> None:
        super().__init__(f"Case with with id '{case_id}' is closed.")

class EmailUnavailableError(DomainError):
    """Raised when an advisor tries to send an unavailable email."""

    def __init__(self, case_id: UUID) -> None:
        super().__init__(f"Email for the case with id '{case_id}' is not available.")

class EmptyEmailError(DomainError):
    """Raised when an advisor tries to send an empty email."""

    def __init__(self, case_id: UUID) -> None:
        super().__init__(f"Email for the case with id '{case_id}' is empty.")

class EmailNotFoundError(DomainError):
    def __init__(self, case_id: UUID):
        super().__init__(
            _NOT_FOUND_MESSAGE_TEMPLATE.format(
                entity='Email',
                id=case_id,
            ),
        )

class MissingReceipentInformationError(DomainError):
    """Raised when the recipent information is missing."""

class DraftGenerationError(DomainError):
    """Base exception for email draft generation failures."""

class ToxicityDetectedError(DraftGenerationError):
    """Raised when toxic content or hate speech is detected in the draft."""

class TonePolicyViolationError(DraftGenerationError):
    """Raised when the draft violates the empathetic tone policy."""




# =============================
# ========== STUDENT ==========
# =============================

class StudentError(DomainError):
    """Base error for Student."""

class StudentEmailNotFoundError(CaseError):
    """"""

class StudentNotFoundError(StudentError):
    """Raised when a student is not found."""

    def __init__(self, student_id: UUID):
        super().__init__(
            _NOT_FOUND_MESSAGE_TEMPLATE.format(
                entity='student',
                id=student_id,
            ),
        )

class MissingPerformanceDataError(StudentError):
    """Raised when a student lacks recent performance data for email generation."""

    def __init__(self, student_id: UUID):
        super().__init__(f"Student {student_id} has no recent performance data.")

class StudentNameMissingError(StudentError):
    """Raised when a student name is missing."""

    def __init__(self, student_id: UUID):
        super().__init__(f"Student {student_id} is missing a name.")

# ==========================
# ========== TASK ==========
# ==========================


class TaskError(DomainError):
    """Base error for task."""


class TaskNotFoundError(TaskError):
    """Raised when a task is not found."""

    def __init__(self, task_id: UUID):
        super().__init__(
            _NOT_FOUND_MESSAGE_TEMPLATE.format(
                entity='task',
                id=task_id,
            ),
        )


class TaskUavailableError(TaskError):
    """Raised when a task is unavailable."""

    def __init__(self, task_id: UUID, current_status: str) -> None:
        super().__init__(
            f"task with id '{task_id}' is unavailable, current status: {current_status}",
        )


# =============================
# ======== Appointment ========
# =============================


class AppointmentError(DomainError):
    """Base error for appointment."""


class TimeSlotUnavailableError(AppointmentError):
    """Raised when a requested time slot is not available for booking."""

    def __init__(self, advisor_id: UUID, requested_time: datetime) -> None:
        super().__init__(
            f"Advisor {advisor_id} is not available at {requested_time}.",
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


class AdvisorProfileNotLinkedError(AdvisorError):
    """Raised when an advisor account not linked to an advisor profile."""

    def __init__(self, user_id: UUID) -> None:
        super().__init__(
            f"account with ID '{user_id}' does not link to any advisor profile.",
        )


class UserIsNotAnAdvisorError(AdvisorError):
    """Raised when an advisor account not linked to an advisor profile."""

    def __init__(self, user_id: UUID) -> None:
        super().__init__(f"account with ID '{user_id}' is not an advisor.")


class WorkingHoursNotFoundError(AdvisorError):
    """Raised when a working hours record is not found."""

    def __init__(self, wh_id: UUID) -> None:
        super().__init__(
            _NOT_FOUND_MESSAGE_TEMPLATE.format(entity='WorkingHours', id=wh_id)
        )


class ValidationError(DomainError):
    """Raised when a domain invariant is violated."""

    pass


class UnauthorizedError(DomainError):
    """Raised when an operation is not permitted in the domain."""

    pass

# =========================
# ========== Job ==========
# =========================

class JobError(DomainError):
    """Base error for job."""

    pass

class JobNotFoundError(JobError):
    """Raised when a job is not found."""
    def __init__(self, job_id: UUID | None = None, correlation_id: UUID | None = None) -> None:
        if job_id is not None:
            msg = _NOT_FOUND_MESSAGE_TEMPLATE.format(
                entity='job',
                id=job_id,
            )
        elif correlation_id is not None:
            msg = _NOT_FOUND_MESSAGE_TEMPLATE.format(
                entity='job_correlation',
                id=correlation_id,
            )
        else:
            raise ValueError("Expected one of (job_id, correlation_id) provided.")

        super().__init__(msg)
