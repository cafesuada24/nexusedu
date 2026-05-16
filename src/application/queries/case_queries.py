"""Query handlers for case-related operations."""


from src.application.dtos.case_dtos import (
    CaseDTO,
    CaseOverviewDTO,
    GetAllCasesQuery,
    GetAssignedQuery,
    GetUnassignedQuery,
    QueryAppointmentDTO,
    QueryEmailDTO,
)
from src.application.dtos.pagination import PagedResponse
from src.application.interfaces.case_query_service import CaseQueryService
from src.core.identifiers import EntityID
from src.domain.exceptions import (
    CaseNotFoundError,
    UserIsNotAnAdvisorError,
)
from src.domain.repositories.advisor_repository import AdvisorRepository
from src.domain.repositories.case_repository import CaseRepository
from src.domain.repositories.email_repository import EmailRepository
from src.domain.repositories.student_repository import StudentRepository


class CaseQueryHandler:
    """Handler for case-related queries."""

    def __init__(
        self,
        case_query_service: CaseQueryService,
        case_repo: CaseRepository,
        advisor_repo: AdvisorRepository,
        email_repo: EmailRepository,
        student_repo: StudentRepository,
    ):
        self._case_query_service = case_query_service
        self._advisor_repo = advisor_repo
        self.__case_repo = case_repo
        self.__email_repo = email_repo
        self.__student_repo = student_repo

    async def handle_get_assigned_cases(
        self,
        query: GetAssignedQuery,
    ) -> PagedResponse[CaseDTO]:
        """Execute the get task list query."""
        advisor = await self._advisor_repo.find_by_user_id(query.user_id)
        if advisor is None:
            raise UserIsNotAnAdvisorError(user_id=query.user_id)

        return await self._case_query_service.find_assigned_to(
            advisor_id=advisor.advisor_id,
            limit=query.limit,
            offset=query.offset,
        )

    async def handle_get_open_cases(
        self,
        query: GetUnassignedQuery,
    ) -> PagedResponse[CaseDTO]:
        """Execute the get task list query."""
        return await self._case_query_service.find_assigned_to(
            advisor_id=None,
            limit=query.limit,
            offset=query.offset,
        )

    async def handle_get_all_cases(
        self,
        query: GetAllCasesQuery,
    ) -> PagedResponse[CaseDTO]:
        """Execute the get all cases query (Admin only)."""
        return await self._case_query_service.find_all(
            limit=query.limit,
            offset=query.offset,
        )

    async def handle_get_case_details(self, case_id: EntityID) -> CaseDTO:
        """Retrieve full details of a specific case, including its associated email."""
        case = await self.__case_repo.get_by_id(case_id)
        advisor = None
        if case.is_assigned:
            advisor = await self._advisor_repo.get_by_id(case.assigned_advisor_id)  # pyright: ignore

        email = await self.__email_repo.find_by_case(case_id)
        student = await self.__student_repo.get_by_id(case.sid)

        return CaseDTO(
            case_id=case.case_id,
            sid=case.sid,
            created_at=case.created_at,
            assigned_advisor_id=case.assigned_advisor_id if advisor else None,
            assigned_to=advisor.name if advisor else None,
            student_name=student.student_name,
            major=student.major,
            current_risk_status=student.current_risk_status,
            intervention_status=case.intervention_status,
            email=QueryEmailDTO(
                email_id=email.email_id,
                recipient=student.email,
                subject=email.subject,
                body=email.body,
                status=email.status,
                created_at=case.created_at,
                sent_at=email.sent_at,
            )
            if email
            else None,
            appointment=QueryAppointmentDTO(
                appointment_time=case.appointment.appointment_time,
                duration_minutes=case.appointment.duration_minutes,
                meeting_method=case.appointment.meeting_method,
                notes=case.appointment.notes,
            )
            if case.appointment
            else None,
            ai_overview=CaseOverviewDTO(
                academic_summary=case.academic_summary,
                action_keys=case.action_keys or [],
            )
            if case.academic_summary
            else None,
        )

    async def handle_get_case_email(
        self,
        case_id: EntityID,
        user_id: EntityID,
    ) -> QueryEmailDTO:
        """Retrieve the current AI email status and content for a case."""
        case = await self.__case_repo.get_by_id(case_id)
        advisor = await self._advisor_repo.get_by_user_id(user_id)
        if advisor.advisor_id != case.assigned_advisor_id:
            raise CaseNotFoundError(case_id)

        student = await self.__student_repo.get_by_id(case.sid)

        # 1. Look for existing email record for this case
        email = await self.__email_repo.get_by_case(case_id)

        return QueryEmailDTO(
            email_id=email.email_id,
            recipient=student.email,
            status=email.status,
            created_at=email.created_at,
            body=email.body,
            subject=email.subject,
        )
