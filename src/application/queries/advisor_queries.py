"""Query handlers for advisor-related operations."""

import json
from dataclasses import dataclass
from uuid import UUID

from arq import ArqRedis

from src.application.dtos.advisor_dtos import (
    BadgeDTO,
    EngagementMetricsDTO,
    LeaderboardEntryDTO,
)
from src.domain.repositories.badge_repository import BadgeRepository
from src.domain.repositories.interfaces import AdvisorRepository
from src.domain.value_objects.badges import BADGE_MAP
from src.presentation.dtos.pagination import PagedResponse, PaginationMetadata


@dataclass(frozen=True)
class GetLeaderboardQuery:
    """Query to retrieve the advisor leaderboard."""

    time_window: str
    limit: int = 10
    offset: int = 0


class AdvisorQueryHandler:
    """Handler for advisor-related queries."""

    def __init__(
        self,
        advisor_repo: AdvisorRepository,
        badge_repo: BadgeRepository,
        arq_pool: ArqRedis,
    ):
        self.advisor_repo = advisor_repo
        self.badge_repo = badge_repo
        self.arq_pool = arq_pool

    async def handle_get_engagement_metrics(self) -> list[EngagementMetricsDTO]:
        """Execute the get engagement metrics query."""
        metrics = await self.advisor_repo.get_engagement_metrics()
        return [
            EngagementMetricsDTO(
                major=m['faculty'],
                sent_count=m['sent'],
                drafted_count=m.get('drafted', 0),
            )
            for m in metrics
        ]

    async def handle_get_leaderboard(
        self,
        query: GetLeaderboardQuery,
    ) -> tuple[list[LeaderboardEntryDTO], int]:
        """Execute the get leaderboard query."""
        items, total_count = await self.advisor_repo.get_leaderboard(
            query.time_window,
            limit=query.limit,
            offset=query.offset,
        )
        return [
            LeaderboardEntryDTO(
                advisor_id=i['advisor_id'],
                name=i['name'],
                total_points=i['total_points'],
                actions_count=i['actions_count'],
                sent_count=i['sent_count'],
                resolved_count=i['resolved_count'],
            )
            for i in items
        ], total_count

    async def handle_get_advisor_badges(self, advisor_id: UUID) -> list[BadgeDTO]:
        """Execute the get advisor badges query with caching."""
        cache_key = f'advisor_badges:{advisor_id}'

        # 1. Try to get from cache
        cached_data = await self.arq_pool.get(cache_key)
        if cached_data:
            data = json.loads(cached_data)
            return [BadgeDTO(**b) for b in data]

        # 2. If not in cache, fetch from DB
        badge_ids = await self.badge_repo.get_advisor_badges(advisor_id)

        badges: list[BadgeDTO] = []
        for b_id in badge_ids:
            if b_id in BADGE_MAP:
                b = BADGE_MAP[b_id]
                badges.append(
                    BadgeDTO(
                        badge_id=b.badge_id,
                        name=b.name,
                        description=b.description,
                        icon=b.icon,
                    ),
                )

        # 3. Store in cache for 5 minutes (300s)
        badges_dict = [
            {
                'badge_id': b.badge_id,
                'name': b.name,
                'description': b.description,
                'icon': b.icon,
            }
            for b in badges
        ]
        await self.arq_pool.setex(cache_key, 300, json.dumps(badges_dict))

        return badges
