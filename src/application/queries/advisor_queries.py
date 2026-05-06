"""Query handlers for advisor-related operations."""

import json
from uuid import UUID

from arq import ArqRedis
from pydantic_extra_types.phone_numbers import PhoneNumber

from src.application.dtos.advisor_dtos import (
    AdvisorProfileDTO,
    BadgeDTO,
    EngagementMetricsDTO,
    GetAdvisorProfileQuery,
    GetLeaderboardQuery,
    LeaderboardEntryDTO,
)
from src.application.interfaces.advisor_query_service import AdvisorQueryService
from src.domain.repositories.badge_repository import BadgeRepository
from src.domain.repositories.interfaces import AdvisorRepository
from src.domain.value_objects.badges import BADGE_MAP


class AdvisorQueryHandler:
    """Handler for advisor-related queries."""

    def __init__(
        self,
        advisor_repo: AdvisorRepository,
        badge_repo: BadgeRepository,
        advisor_query_service: AdvisorQueryService,
        # arq_pool: ArqRedis,
    ):
        self.__advisor_repo = advisor_repo
        self.__badge_repo = badge_repo
        # self.__arq_pool = arq_pool
        self.__advisor_query_service = advisor_query_service

    async def handle_get_user_advisor_profile(
        self,
        user_id: UUID,
    ) -> AdvisorProfileDTO:
        advisor = await self.__advisor_repo.get_by_user_id(user_id)
        subquery = GetAdvisorProfileQuery(
            advisor_id=advisor.advisor_id,
            include_metrics=False,
        )
        return await self.handle_get_advisor_profile(subquery)

    async def handle_get_advisor_profile(
        self, query: GetAdvisorProfileQuery
    ) -> AdvisorProfileDTO:
        advisor = await self.__advisor_repo.get_by_id(advisor_id=query.advisor_id)
        return AdvisorProfileDTO(
            advisor_id=query.advisor_id,
            name=advisor.name,
            email=advisor.email,
            title=advisor.title,
            phone=PhoneNumber(advisor.phone) if advisor.phone else None,
            faculty=advisor.faculty,
            office=advisor.office,
            bio=advisor.bio,
        )

    async def handle_get_user_advisor_points(self, user_id: UUID) -> int:
        advisor = await self.__advisor_repo.get_by_user_id(user_id)
        return await self.__advisor_query_service.get_advisor_points(
            advisor_id=advisor.advisor_id,
        )

    async def handle_get_advisor_points(self, advisor_id: UUID) -> int:
        return await self.__advisor_query_service.get_advisor_points(
            advisor_id=advisor_id,
        )

    async def handle_get_engagement_metrics(self) -> list[EngagementMetricsDTO]:
        """Execute the get engagement metrics query."""
        ...
        # metrics = await self.__advisor_repo.get_engagement_metrics()
        # return [
        #     EngagementMetricsDTO(
        #         major=m['faculty'],
        #         sent_count=m['sent'],
        #         drafted_count=m.get('drafted', 0),
        #     )
        #     for m in metrics
        # ]

    async def handle_get_leaderboard(
        self,
        query: GetLeaderboardQuery,
    ) -> tuple[list[LeaderboardEntryDTO], int]:
        """Execute the get leaderboard query."""
        ...
        # items, total_count = await self.__advisor_repo.get_leaderboard(
        #     query.time_window,
        #     limit=query.limit,
        #     offset=query.offset,
        # )
        # return [
        #     LeaderboardEntryDTO(
        #         advisor_id=i['advisor_id'],
        #         name=i['name'],
        #         total_points=i['total_points'],
        #         actions_count=i['actions_count'],
        #         sent_count=i['sent_count'],
        #         resolved_count=i['resolved_count'],
        #     )
        #     for i in items
        # ], total_count

    async def handle_get_advisor_badges(self, advisor_id: UUID) -> list[BadgeDTO]:
        """Execute the get advisor badges query with caching."""
        return []
        # cache_key = f'advisor_badges:{advisor_id}'
        #
        # # 1. Try to get from cache
        # cached_data = await self.__arq_pool.get(cache_key)
        # if cached_data:
        #     data = json.loads(cached_data)
        #     return [BadgeDTO(**b) for b in data]
        #
        # # 2. If not in cache, fetch from DB
        # badge_ids = await self.__badge_repo.get_advisor_badges(advisor_id)
        #
        # badges: list[BadgeDTO] = []
        # for b_id in badge_ids:
        #     if b_id in BADGE_MAP:
        #         b = BADGE_MAP[b_id]
        #         badges.append(
        #             BadgeDTO(
        #                 badge_id=b.badge_id,
        #                 name=b.name,
        #                 description=b.description,
        #                 icon=b.icon,
        #             ),
        #         )
        #
        # # 3. Store in cache for 5 minutes (300s)
        # badges_dict = [
        #     {
        #         'badge_id': b.badge_id,
        #         'name': b.name,
        #         'description': b.description,
        #         'icon': b.icon,
        #     }
        #     for b in badges
        # ]
        # await self.__arq_pool.setex(cache_key, 300, json.dumps(badges_dict))
        #
        # return badges
