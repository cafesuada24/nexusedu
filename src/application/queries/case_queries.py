"""Query handlers for case-related operations."""

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from src.application.dtos.case_dtos import (
    CaseDTO,
    GetAssignedQuery,
    GetUnassignedQuery,
)
from src.application.dtos.student_dtos import EmailDTO
from src.application.interfaces.case_query_service import CaseQueryService
from src.domain.exceptions import UserIsNotAnAdvisorError
from src.domain.repositories.advisor_repository import AdvisorRepository
from src.domain.repositories.case_repository import CaseRepository
from src.domain.repositories.email_repository import EmailRepository
from src.domain.repositories.job_repository import JobRepository


class CaseQueryHandler:
    """Handler for case-related queries."""

    def __init__(
        self,
        case_query_service: CaseQueryService,
        case_repo: CaseRepository,
        advisor_repo: AdvisorRepository,
        email_repo: EmailRepository,
        job_repo: JobRepository,
    ):
        self._case_query_service = case_query_service
        self._advisor_repo = advisor_repo
        self.__case_repo = case_repo
        self.__email_repo = email_repo
        self.__job_repo = job_repo

    async def handle_get_assigned_cases(
        self,
        query: GetAssignedQuery,
    ) -> tuple[list[CaseDTO], int]:
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
    ) -> tuple[list[CaseDTO], int]:
        """Execute the get task list query."""
        return await self._case_query_service.find_assigned_to(
            advisor_id=None,
            limit=query.limit,
            offset=query.offset,
        )

    async def handle_get_email_history(
        self,
        sid: UUID,
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
        return {}
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
        case = await self.__case_repo.get_by_id(case_id)
        if not case:
            raise ValueError(f'Case {case_id} not found.')

        # 1. Look for existing email record for this case
        email = await self.__email_repo.get_by_case(case_id)

        is_generating = False
        progress = 0
        subject = None
        body = None

        if email:
            is_generating = email.status.value == 'generating'
            subject = email.subject
            body = email.body

            # 2. If generating, optionally fetch fine-grained progress from JobRepository
            if is_generating:
                active_job = await self.__job_repo.get_active_job(
                    case_id, 'case', 'email_draft',
                )
                if active_job:
                    job_details = await self.__job_repo.get_job(active_job)
                    if job_details:
                        progress = job_details.get('progress', 0)

        return {
            'sid': str(case.sid),
            'is_generating': is_generating,
            'progress': progress,
            'subject': subject,
            'body': body,
            'active_case_id': str(case.case_id),
        }
