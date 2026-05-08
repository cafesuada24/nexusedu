"""Advisor metrics query service implementation."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dtos.advisor_dtos import PersonalAdvisorMetricsDTO
from src.infrastructure.database.models import Case, PointLedger


class SqlAlchemyAdvisorMetricsQueryService:
    """SqlAlchemy implementation for Advisor metrics query service."""

    FAST_ACTION_THRESHOLD_HOURS = 12.0

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with a SQLAlchemy async session."""
        self.__session = session

    async def get_advisor_metrics(
        self,
        advisor_id: UUID,
    ) -> PersonalAdvisorMetricsDTO:
        """Calculate and retrieve personal performance metrics for an advisor."""
        # 1. Basic aggregates from PointLedger
        # Total points, total actions, total resolves
        stmt = (
            select(
                func.coalesce(func.sum(PointLedger.points), 0).label('total_points'),
                func.count(PointLedger.id).label('total_actions'),
                func.count(
                    func.case(
                        (PointLedger.action == 'resolve_case', 1),
                        else_=None,
                    ),
                ).label('total_resolves'),
            )
            .where(PointLedger.advisor_id == advisor_id)
        )

        res = await self.__session.execute(stmt)
        ledger_row = res.fetchone()

        total_points = ledger_row.total_points if ledger_row else 0
        total_actions = ledger_row.total_actions if ledger_row else 0
        total_resolves = ledger_row.total_resolves if ledger_row else 0

        # 2. Performance Metrics from Cases
        # Fast actions (resolved within 12 hours) and Avg Response Hours
        # We need to join Cases with PointLedger for 'resolve_case' actions
        stmt_cases = (
            select(
                Case.created_at,
                PointLedger.earned_at,
            )
            .join(PointLedger, Case.case_id == PointLedger.case_id)
            .where(
                Case.assigned_advisor_id == advisor_id,
                PointLedger.action == 'resolve_case',
            )
        )

        res_cases = await self.__session.execute(stmt_cases)
        rows = res_cases.fetchall()

        total_hours = 0.0
        fast_action_count = 0
        valid_pairs = 0

        for created_at, action_time in rows:
            if created_at and action_time:
                # Ensure they are UTC aware for calculation
                c_at = created_at if created_at.tzinfo else created_at.replace(tzinfo=UTC)
                a_at = action_time if action_time.tzinfo else action_time.replace(tzinfo=UTC)

                delta = (a_at - c_at).total_seconds() / 3600.0
                if delta < 0:
                    delta = 0.0

                total_hours += delta
                valid_pairs += 1
                if delta <= self.FAST_ACTION_THRESHOLD_HOURS:
                    fast_action_count += 1

        avg_response_hours = total_hours / valid_pairs if valid_pairs > 0 else 0.0

        # 3. Recovery Rate (Resolves / Total Cases Assigned)
        stmt_total_cases = (
            select(func.count(Case.case_id))
            .where(Case.assigned_advisor_id == advisor_id)
        )
        res_total = await self.__session.execute(stmt_total_cases)
        total_assigned_cases = res_total.scalar() or 0

        recovery_rate = (total_resolves / total_assigned_cases) * 100.0 if total_assigned_cases > 0 else 0.0

        return PersonalAdvisorMetricsDTO(
            total_points=total_points,
            total_actions=total_actions,
            total_resolves=total_resolves,
            fast_action_count=fast_action_count,
            avg_response_hours=round(avg_response_hours, 1),
            recovery_rate=round(recovery_rate, 1),
        )
