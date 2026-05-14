"""Advisor metrics query service implementation."""

from datetime import UTC, datetime

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dtos.advisor_dtos import PersonalAdvisorMetricsDTO
from src.application.dtos.metrics_dtos import (
    EmergencyDashboardDTO,
    ImpactHistoryDTO,
    ImpactMetricDTO,
    RecoveryMetricDTO,
    ResponseKpiMetricDTO,
)
from src.core.identifiers import EntityID
from src.domain.value_objects.status import EmailStatus, InterventionStatus, RiskStatus
from src.infrastructure.database.models import (
    Case,
    InterventionEmail,
    PointLedger,
    Student,
)


class SqlAlchemyAdvisorMetricsQueryService:
    """SqlAlchemy implementation for Advisor metrics query service."""

    FAST_ACTION_THRESHOLD_HOURS = 12.0

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with a SQLAlchemy async session."""
        self.__session = session

    async def get_advisor_metrics(
        self,
        advisor_id: EntityID,
    ) -> PersonalAdvisorMetricsDTO:
        """Calculate and retrieve personal performance metrics for an advisor."""
        # 1. Basic aggregates from PointLedger
        # Total points, total actions, total resolves
        stmt = select(
            func.coalesce(func.sum(PointLedger.points), 0).label('total_points'),
            func.count(PointLedger.id).label('total_actions'),
            func.count(
                case(
                    (PointLedger.action == 'resolve_case', 1),
                    else_=None,
                ),
            ).label('total_resolves'),
        ).where(PointLedger.advisor_id == advisor_id)

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
                c_at = (
                    created_at if created_at.tzinfo else created_at.replace(tzinfo=UTC)
                )
                a_at = (
                    action_time
                    if action_time.tzinfo
                    else action_time.replace(tzinfo=UTC)
                )

                delta = (a_at - c_at).total_seconds() / 3600.0
                if delta < 0:
                    delta = 0.0

                total_hours += delta
                valid_pairs += 1
                if delta <= self.FAST_ACTION_THRESHOLD_HOURS:
                    fast_action_count += 1

        avg_response_hours = total_hours / valid_pairs if valid_pairs > 0 else 0.0

        # 3. Recovery Rate (Resolves / Total Cases Assigned)
        stmt_total_cases = select(func.count(Case.case_id)).where(
            Case.assigned_advisor_id == advisor_id
        )
        res_total = await self.__session.execute(stmt_total_cases)
        total_assigned_cases = res_total.scalar() or 0

        recovery_rate = (
            (total_resolves / total_assigned_cases) * 100.0
            if total_assigned_cases > 0
            else 0.0
        )

        return PersonalAdvisorMetricsDTO(
            total_points=total_points,
            total_actions=total_actions,
            total_resolves=total_resolves,
            fast_action_count=fast_action_count,
            avg_response_hours=round(avg_response_hours, 1),
            recovery_rate=round(recovery_rate, 1),
        )

    async def get_emergency_dashboard(
        self,
        advisor_id: EntityID,
    ) -> EmergencyDashboardDTO:
        """Calculate and retrieve aggregate emergency dashboard metrics for an advisor."""
        # 1. Priority Queue: Active cases with Elevated/Critical risk students
        stmt_pq = (
            select(func.count(Case.case_id))
            .join(Student, Case.sid == Student.sid)
            .where(
                Case.assigned_advisor_id == advisor_id,
                Case.intervention_status.in_(
                    [
                        InterventionStatus.NEW,
                        InterventionStatus.ACCEPTED,
                        InterventionStatus.SENT,
                        InterventionStatus.BOOKED,
                        InterventionStatus.SUPPORTING,
                        InterventionStatus.PENDING_REVIEW,
                    ],
                ),
                Student.current_risk_status.in_(
                    [RiskStatus.ELEVATED, RiskStatus.CRITICAL],
                ),
            )
        )
        priority_queue = (await self.__session.execute(stmt_pq)).scalar() or 0

        # 2. Response KPI
        # Get first response time for each case assigned to this advisor
        first_responses_sub = (
            select(
                PointLedger.case_id,
                func.min(PointLedger.earned_at).label('first_response_at'),
            )
            .where(PointLedger.advisor_id == advisor_id)
            .group_by(PointLedger.case_id)
        ).subquery()

        stmt_kpi = (
            select(
                Case.created_at,
                first_responses_sub.c.first_response_at,
            )
            .join(first_responses_sub, Case.case_id == first_responses_sub.c.case_id)
            .where(Case.assigned_advisor_id == advisor_id)
        )
        kpi_rows = (await self.__session.execute(stmt_kpi)).fetchall()

        total_kpi_hours = 0.0
        sla_breach_count = 0
        kpi_count = len(kpi_rows)
        target_hours = 4.0

        for c_at, r_at in kpi_rows:
            c_at_utc = (
                c_at.replace(tzinfo=UTC)
                if c_at.tzinfo is None
                else c_at.astimezone(UTC)
            )
            r_at_utc = (
                r_at.replace(tzinfo=UTC)
                if r_at.tzinfo is None
                else r_at.astimezone(UTC)
            )

            diff_hours = (r_at_utc - c_at_utc).total_seconds() / 3600.0
            diff_hours = max(diff_hours, 0)
            total_kpi_hours += diff_hours
            if diff_hours > target_hours:
                sla_breach_count += 1

        avg_kpi_hours = total_kpi_hours / kpi_count if kpi_count > 0 else 0.0
        within_kpi_rate = (
            (kpi_count - sla_breach_count) / kpi_count if kpi_count > 0 else 1.0
        )

        response_kpi = ResponseKpiMetricDTO(
            avg_response_hours=round(avg_kpi_hours, 2),
            target_hours=target_hours,
            within_kpi_rate=within_kpi_rate,
            sla_breach_count=sla_breach_count,
        )

        # 3. Activation Rate
        # Cases with SENT emails that progressed to engagement status
        stmt_emails_sent = (
            select(func.count(InterventionEmail.case_id))
            .join(Case)
            .where(
                Case.assigned_advisor_id == advisor_id,
                InterventionEmail.status == EmailStatus.SENT,
            )
        )
        emails_sent_count = (
            await self.__session.execute(stmt_emails_sent)
        ).scalar() or 0

        stmt_activated = select(func.count(Case.case_id)).where(
            Case.assigned_advisor_id == advisor_id,
            Case.intervention_status.in_(
                [
                    InterventionStatus.BOOKED,
                    InterventionStatus.SUPPORTING,
                    InterventionStatus.PENDING_REVIEW,
                    InterventionStatus.RESOLVED,
                ],
            ),
        )
        activated_count = (await self.__session.execute(stmt_activated)).scalar() or 0
        activation = (
            min(1.0, activated_count / emails_sent_count)
            if emails_sent_count > 0
            else 0.0
        )

        # 4. Recovery Rate
        # Students who recovered (current status NORMAL) / Total distinct students assisted
        stmt_total_students = select(func.count(func.distinct(Case.sid))).where(
            Case.assigned_advisor_id == advisor_id,
        )
        total_risk_students = (
            await self.__session.execute(stmt_total_students)
        ).scalar() or 0

        stmt_stabilized = (
            select(func.count(func.distinct(Student.sid)))
            .join(Case, Student.sid == Case.sid)
            .where(
                Case.assigned_advisor_id == advisor_id,
                Student.current_risk_status == RiskStatus.NORMAL,
            )
        )
        stabilized_students = (
            await self.__session.execute(stmt_stabilized)
        ).scalar() or 0
        recovery_rate = (
            stabilized_students / total_risk_students
            if total_risk_students > 0
            else 0.0
        )

        stmt_recovery_time = select(Case.created_at, Case.closed_at).where(
            Case.assigned_advisor_id == advisor_id,
            Case.intervention_status == InterventionStatus.RESOLVED,
            Case.closed_at.isnot(None),
        )
        recovery_rows = (await self.__session.execute(stmt_recovery_time)).fetchall()
        total_recovery_days = sum((cl_at - c_at).days for c_at, cl_at in recovery_rows)
        avg_recovery_days = (
            total_recovery_days / len(recovery_rows) if recovery_rows else 0.0
        )

        recovery = RecoveryMetricDTO(
            recovery_rate=recovery_rate,
            stabilized_students=stabilized_students,
            total_risk_students=total_risk_students,
            avg_recovery_days=avg_recovery_days,
        )

        # 5. Impact Metric
        stmt_xp = select(func.coalesce(func.sum(PointLedger.points), 0)).where(
            PointLedger.advisor_id == advisor_id,
        )
        current_xp = (await self.__session.execute(stmt_xp)).scalar() or 0

        stmt_resolved = select(func.count(Case.case_id)).where(
            Case.assigned_advisor_id == advisor_id,
            Case.intervention_status == InterventionStatus.RESOLVED,
        )
        resolved_count = (await self.__session.execute(stmt_resolved)).scalar() or 0

        stmt_total_assigned = select(func.count(Case.case_id)).where(
            Case.assigned_advisor_id == advisor_id,
        )
        total_assigned = (
            await self.__session.execute(stmt_total_assigned)
        ).scalar() or 0
        completion_rate = resolved_count / total_assigned if total_assigned > 0 else 0.0

        rank_stmt = (
            select(
                PointLedger.advisor_id,
                func.rank()
                .over(order_by=func.sum(PointLedger.points).desc())
                .label('rank'),
            )
            .group_by(PointLedger.advisor_id)
            .subquery()
        )

        stmt_my_rank = select(rank_stmt.c.rank).where(
            rank_stmt.c.advisor_id == advisor_id,
        )
        ranking_position = (await self.__session.execute(stmt_my_rank)).scalar()

        now = datetime.now(UTC)
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        stmt_weekly = select(PointLedger.earned_at, PointLedger.points).where(
            PointLedger.advisor_id == advisor_id,
            PointLedger.earned_at >= start_of_month,
        )
        weekly_rows = (await self.__session.execute(stmt_weekly)).fetchall()

        weekly_xp_map: dict[int, int] = {}
        for earned_at, points in weekly_rows:
            week_num: int = earned_at.isocalendar()[1]
            weekly_xp_map[week_num] = weekly_xp_map.get(week_num, 0) + points

        weekly_history = [
            ImpactHistoryDTO(week=w, xp=x) for w, x in sorted(weekly_xp_map.items())
        ]

        impact = ImpactMetricDTO(
            current_xp=current_xp,
            completion_rate=completion_rate,
            ranking_position=ranking_position,
            month=now.month,
            year=now.year,
            weekly_history=weekly_history,
        )

        return EmergencyDashboardDTO(
            priority_queue=priority_queue,
            response_kpi=response_kpi,
            activation=activation,
            recovery=recovery,
            impact=impact,
        )
