"""Query handlers for advisor-related operations."""

from datetime import date, timedelta
from uuid import UUID

from pydantic_extra_types.phone_numbers import PhoneNumber

from src.application.dtos.advisor_dtos import (
    AdvisorProfileDTO,
    AdvisorScheduleDTO,
    AvailabilitySlotDTO,
    BadgeDTO,
    DayOffDTO,
    GetAdvisorAvailabilityQuery,
    GetAdvisorProfileQuery,
    GetAdvisorScheduleQuery,
    GetUserAdvisorScheduleQuery,
    PersonalAdvisorMetricsDTO,
    WorkingHoursDTO,
)
from src.application.dtos.gamification_dtos import (
    GetLeaderboardQuery,
    LeaderboardEntryDTO,
)
from src.application.dtos.pagination import PagedResponse
from src.application.interfaces.advisor_metrics_query_service import (
    AdvisorMetricsQueryService,
)
from src.application.interfaces.availability_query_service import (
    AdvisorAvailabilityQueryService,
)
from src.application.interfaces.gamification_query_service import (
    GamificationQueryService,
)
from src.application.interfaces.ledger_query_service import PointLedgerQueryService
from src.domain.exceptions import UserIsNotAnAdvisorError
from src.domain.repositories.interfaces import AdvisorRepository
from src.domain.repositories.schedule_repository import ScheduleRepository


class AdvisorQueryHandler:
    """Handler for advisor-related queries."""

    def __init__(
        self,
        advisor_repo: AdvisorRepository,
        schedule_repo: ScheduleRepository,
        point_ledger_query_service: PointLedgerQueryService,
        gamification_query_service: GamificationQueryService,
        advisor_metrics_query_service: AdvisorMetricsQueryService,
        availability_query_service: AdvisorAvailabilityQueryService,
    ) -> None:
        """Initialize with required repositories and services."""
        self.__advisor_repo = advisor_repo
        self.__schedule_repo = schedule_repo
        self.__point_ledger_query_service = point_ledger_query_service
        self.__gamification_query_service = gamification_query_service
        self.__advisor_metrics_query_service = advisor_metrics_query_service
        self.__availability_query_service = availability_query_service

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
            advisor_id,
        )

    async def handle_get_advisor_badges(self, advisor_id: UUID) -> list[BadgeDTO]:
        """Execute the get advisor badges query with caching."""
        _ = advisor_id
        return []

    async def handle_get_advisor_availability(
        self,
        query: GetAdvisorAvailabilityQuery,
    ) -> list[AvailabilitySlotDTO]:
        """Execute the get advisor availability query."""
        slots = await self.__availability_query_service.get_available_slots(
            query.advisor_id,
            query.start_date,
            query.end_date,
        )
        return [
            AvailabilitySlotDTO(
                start_time=slot,
                end_time=slot + timedelta(minutes=30),
            )
            for slot in slots
        ]

    async def handle_get_user_advisor_schedule(
        self,
        query: GetUserAdvisorScheduleQuery,
    ) -> AdvisorScheduleDTO:
        """Execute the get advisor schedule query."""
        advisor = await self.__advisor_repo.find_by_user_id(query.user_id)
        if advisor is None:
            raise UserIsNotAnAdvisorError(query.user_id)

        transfer_query = GetAdvisorScheduleQuery(advisor_id=advisor.advisor_id)
        return await self.handle_get_advisor_schedule(transfer_query)

    async def handle_get_advisor_schedule(
        self,
        query: GetAdvisorScheduleQuery,
    ) -> AdvisorScheduleDTO:
        """Execute the get advisor schedule query."""
        # 1. Fetch raw data from schedule repo
        working_hours = await self.__schedule_repo.get_working_hours(query.advisor_id)
        # Fetch days off for a reasonable range (e.g., 3 months)

        days_off = await self.__schedule_repo.get_days_off(
            query.advisor_id,
            date.today(),
            date.today() + timedelta(days=90),
        )

        return AdvisorScheduleDTO(
            working_hours=[
                WorkingHoursDTO(
                    id=wh.id,
                    day_of_week=wh.day_of_week,
                    start_time=wh.start_time,
                    end_time=wh.end_time,
                    timezone=wh.timezone,
                )
                for wh in working_hours
            ],
            days_off=[
                DayOffDTO(id=do.id, date=do.date, reason=do.reason) for do in days_off
            ],
        )
