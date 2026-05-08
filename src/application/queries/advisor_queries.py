"""Query handlers for advisor-related operations."""

from uuid import UUID

from pydantic_extra_types.phone_numbers import PhoneNumber

from src.application.dtos.advisor_dtos import (
    AdvisorProfileDTO,
    BadgeDTO,
    GetAdvisorProfileQuery,
    PersonalAdvisorMetricsDTO,
)
from src.application.dtos.gamification_dtos import (
    GetLeaderboardQuery,
    LeaderboardEntryDTO,
)
from src.application.dtos.pagination import PagedResponse
from src.application.interfaces.advisor_metrics_query_service import (
    AdvisorMetricsQueryService,
)
from src.application.interfaces.gamification_query_service import (
    GamificationQueryService,
)
from src.application.interfaces.ledger_query_service import PointLedgerQueryService
from src.domain.repositories.interfaces import AdvisorRepository


class AdvisorQueryHandler:
    """Handler for advisor-related queries."""

    def __init__(
        self,
        advisor_repo: AdvisorRepository,
        point_ledger_query_service: PointLedgerQueryService,
        gamification_query_service: GamificationQueryService,
        advisor_metrics_query_service: AdvisorMetricsQueryService,
    ) -> None:
        """Initialize with required repositories and services."""
        self.__advisor_repo = advisor_repo
        self.__point_ledger_query_service = point_ledger_query_service
        self.__gamification_query_service = gamification_query_service
        self.__advisor_metrics_query_service = advisor_metrics_query_service

    async def handle_get_user_advisor_profile(
        self,
        user_id: UUID,
    ) -> AdvisorProfileDTO:
        """Retrieve the advisor profile associated with a user ID."""
        advisor = await self.__advisor_repo.get_by_user_id(user_id)
        subquery = GetAdvisorProfileQuery(
            advisor_id=advisor.advisor_id,
            include_metrics=False,
        )
        return await self.handle_get_advisor_profile(subquery)

    async def handle_get_advisor_profile(
        self,
        query: GetAdvisorProfileQuery,
    ) -> AdvisorProfileDTO:
        """Retrieve a specific advisor profile by advisor ID."""
        advisor = await self.__advisor_repo.get_by_id(advisor_id=query.advisor_id)

        personal_metrics = None
        if query.include_metrics:
            personal_metrics = (
                await self.__advisor_metrics_query_service.get_advisor_metrics(
                    query.advisor_id,
                )
            )

        return AdvisorProfileDTO(
            advisor_id=query.advisor_id,
            name=advisor.name,
            email=advisor.email,
            title=advisor.title,
            phone=PhoneNumber(advisor.phone) if advisor.phone is not None else None,
            faculty=advisor.faculty,
            office=advisor.office,
            bio=advisor.bio,
            personal_metrics=personal_metrics,
        )

    async def handle_get_user_advisor_points(self, user_id: UUID) -> int:
        """Retrieve total points for the advisor associated with a user ID."""
        advisor = await self.__advisor_repo.get_by_user_id(user_id)
        return await self.__point_ledger_query_service.get_total_points(
            advisor_id=advisor.advisor_id,
        )

    async def handle_get_leaderboard(
        self,
        query: GetLeaderboardQuery,
    ) -> PagedResponse[LeaderboardEntryDTO]:
        """Execute the get leaderboard query."""
        return await self.__gamification_query_service.get_leaderboard(
            time_window=query.time_window,
            limit=query.limit,
            offset=query.offset,
        )

    async def handle_get_advisor_metrics(
        self,
        advisor_id: UUID,
    ) -> PersonalAdvisorMetricsDTO:
        """Execute the get advisor metrics query."""
        # Ensure advisor exists
        await self.__advisor_repo.get_by_id(advisor_id)
        return await self.__advisor_metrics_query_service.get_advisor_metrics(
            advisor_id
        )

    async def handle_get_advisor_badges(self, advisor_id: UUID) -> list[BadgeDTO]:
        """Execute the get advisor badges query with caching."""
        _ = advisor_id
        return []
