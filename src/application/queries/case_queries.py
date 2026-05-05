"""Query handlers for case-related operations."""

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from src.application.dtos.case_dtos import CaseDTO
from src.application.dtos.student_dtos import EmailDTO
from src.application.exceptions import MissingAdvisorProfileError
from src.application.interfaces.case_query_service import CaseQueryService
from src.domain.repositories.advisor_repository import AdvisorRepository


@dataclass
class GetEmailHistoryQuery:
    """Query to retrieve communication history for a student."""

    sid: UUID


@dataclass(frozen=True)
class GetAssignedQuery:
    """Query to retrieve advisor task list."""

    user_id: UUID
    limit: int = 20
    offset: int = 0


@dataclass(frozen=True)
class GetUnassignedQuery:
    """Query to retrieve advisor task list."""

    limit: int = 20
    offset: int = 0


class CaseQueryHandler:
    """Handler for case-related queries."""

    def __init__(
        self,
        case_query_service: CaseQueryService,
        advisor_repo: AdvisorRepository,
    ):
        self._case_query_service = case_query_service
        self._advisor_repo = advisor_repo

    async def handle_get_assigned_cases(
        self,
        query: GetAssignedQuery,
    ) -> tuple[list[CaseDTO], int]:
        """Execute the get task list query."""
        advisor = await self._advisor_repo.get_by_user_id(query.user_id)
        if advisor is None:
            raise MissingAdvisorProfileError(user_id=query.user_id)

        return await self._case_query_service.find_assigned_to(
            advisor_id=advisor.advisor_id,
            limit=query.limit,
            offset=query.offset,
        )

    async def handle_get_open_cases(
        self,
        query: GetUnassignedQuery,
    ) -> tuple[list[CaseDTO], int]:
        """Execute the get task list query."""
        return await self._case_query_service.find_assigned_to(
            advisor_id=None,
            limit=query.limit,
            offset=query.offset,
        )

    async def handle_get_email_history(
        self,
        query: GetEmailHistoryQuery,
    ) -> list[EmailDTO]:
        """Execute the get email history query."""
        return []
        # domain_emails = await self.email_repo.get_history(query.sid)
        # return [
        #     EmailDTO(
        #         email_id=e.email_id,
        #         sid=e.sid,
        #         subject=e.subject,
        #         body=e.body,
        #         status=e.status.value,
        #         created_at=e.created_at.isoformat(),
        #         sent_at=e.sent_at.isoformat() if e.sent_at else None,
        #     )
        #     for e in domain_emails
        # ]

    async def handle_get_case_details(self, case_id: UUID) -> dict[str, Any]:
        """Retrieve full details of a specific case, including its associated email."""
        return []
        # case = await self.case_repo.get_by_id(case_id)
        # if not case:
        #     raise ValueError(f'Case {case_id} not found.')
        #
        # email = await self.email_repo.get_by_case(case_id)
        #
        # return {
        #     'case_id': str(case.case_id),
        #     'sid': str(case.sid),
        #     'status': case.status.value,
        #     'created_at': case.created_at.isoformat(),
        #     'resolved_at': case.closed_at.isoformat() if case.closed_at else None,
        #     'email': {
        #         'email_id': str(email.email_id),
        #         'subject': email.subject,
        #         'body': email.body,
        #         'status': email.status.value,
        #         'created_at': email.created_at.isoformat(),
        #         'sent_at': email.sent_at.isoformat() if email.sent_at else None,
        #     }
        #     if email
        #     else None,
        # }

    async def handle_get_draft_status(self, case_id: UUID) -> dict[str, Any]:
        """Retrieve the current AI draft status and content for a case."""
        return {}
        # case = await self.case_repo.get_by_id(case_id)
        # if not case:
        #     raise ValueError(f'Case {case_id} not found.')
        #
        # # 1. Look for existing email record for this case
        # email = await self.email_repo.get_by_case(case_id)
        #
        # is_generating = False
        # progress = 0
        # subject = None
        # body = None
        #
        # if email:
        #     is_generating = email.status.value == 'generating'
        #     subject = email.subject
        #     body = email.body
        #
        #     # 2. If generating, optionally fetch fine-grained progress from JobRepository
        #     if is_generating:
        #         active_job = await self.job_repo.get_active_job(
        #             case_id, 'case', 'email_draft'
        #         )
        #         if active_job:
        #             job_details = await self.job_repo.get_job(active_job)
        #             if job_details:
        #                 progress = job_details.get('progress', 0)
        #
        # return {
        #     'sid': str(case.sid),
        #     'is_generating': is_generating,
        #     'progress': progress,
        #     'subject': subject,
        #     'body': body,
        #     'active_case_id': str(case.case_id),
        # }
