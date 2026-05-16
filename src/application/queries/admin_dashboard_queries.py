"""Query service for the Admin Dashboard."""

from sqlalchemy import and_, case, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dtos.admin_dashboard_dtos import (
    AcademicImpactMetricDTO,
    AdminDashboardDTO,
    LeadTimeMetricDTO,
    MajorRiskMetricDTO,
    NudgeActivationMetricDTO,
    RecoveryMetricDTO,
    RiskDistributionDTO,
    SystemicRiskMetricDTO,
    TrendDistributionDTO,
)
from src.domain.value_objects.status import (
    InterventionStatus,
    RiskStatus,
)
from src.infrastructure.database.models import (
    Case,
    InterventionEmail,
    Student,
    StudentStatusHistory,
)

TARGET_LEAD_TIME_HOURS = 4.0


class AdminDashboardQueryService:
    """Service for querying Admin Dashboard metrics."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with an active database session."""
        self.session = session

    async def get_dashboard_data(self) -> AdminDashboardDTO:
        """Fetch and aggregate all dashboard metrics."""
        return AdminDashboardDTO(
            recovery=await self._get_recovery_metrics(),
            lead_time=await self._get_lead_time_metrics(),
            nudge_activation=await self._get_nudge_activation_metrics(),
            academic_impact=await self._get_academic_impact_metrics(),
            risk_distribution=await self._get_risk_distribution(),
            major_risk=await self._get_major_risk_metrics(),
            systemic_risk=await self._get_systemic_risk_metrics(),
            trend_distribution=await self._get_trend_distribution(),
        )

    async def _get_systemic_risk_metrics(self) -> SystemicRiskMetricDTO:
        """Calculate School-wide Breadth Metrics."""
        # Latest breadth per student
        latest_history_subq = select(
            StudentStatusHistory.sid,
            StudentStatusHistory.systemic_breadth,
            func.row_number()
            .over(
                partition_by=StudentStatusHistory.sid,
                order_by=[
                    desc(StudentStatusHistory.academic_year),
                    desc(StudentStatusHistory.semester),
                    desc(StudentStatusHistory.week),
                ],
            )
            .label('rn'),
        ).subquery()

        stmt = select(
            func.avg(latest_history_subq.c.systemic_breadth),
            func.count(case((latest_history_subq.c.systemic_breadth > 0.5, 1))),
        ).where(latest_history_subq.c.rn == 1)

        result = (await self.session.execute(stmt)).first()
        avg_breadth = float(result[0]) if result and result[0] is not None else 0.0
        count = int(result[1]) if result else 0

        return SystemicRiskMetricDTO(avg_breadth=avg_breadth, systemic_case_count=count)

    async def _get_trend_distribution(self) -> TrendDistributionDTO:
        """Calculate overall trend direction of the student population."""
        # Latest trend per student
        latest_history_subq = select(
            StudentStatusHistory.sid,
            StudentStatusHistory.trend_score,
            func.row_number()
            .over(
                partition_by=StudentStatusHistory.sid,
                order_by=[
                    desc(StudentStatusHistory.academic_year),
                    desc(StudentStatusHistory.semester),
                    desc(StudentStatusHistory.week),
                ],
            )
            .label('rn'),
        ).subquery()

        stmt = select(
            func.count(case((latest_history_subq.c.trend_score > 0.1, 1))),
            func.count(case((latest_history_subq.c.trend_score < -0.1, 1))),
            func.count(
                case(
                    (
                        and_(
                            latest_history_subq.c.trend_score >= -0.1,
                            latest_history_subq.c.trend_score <= 0.1,
                        ),
                        1,
                    )
                )
            ),
        ).where(latest_history_subq.c.rn == 1)

        result = (await self.session.execute(stmt)).first()
        improving = int(result[0]) if result else 0
        declining = int(result[1]) if result else 0
        stable = int(result[2]) if result else 0

        return TrendDistributionDTO(
            improving=improving, declining=declining, stable=stable
        )

    async def _get_recovery_metrics(self) -> RecoveryMetricDTO:
        """Calculate Overall Recovery Rate."""
        # Total unique students who had a case (meaning they were at risk at some point)
        total_stmt = select(func.count(func.distinct(Case.sid)))
        total_ever_at_risk = (await self.session.execute(total_stmt)).scalar() or 0

        # Students recovered: previously at risk (has a case) and now NORMAL
        recovered_stmt = (
            select(func.count(func.distinct(Case.sid)))
            .join(
                Student,
                Case.sid == Student.sid,
            )
            .where(
                Student.current_risk_status == RiskStatus.NORMAL,
            )
        )
        stabilized = (await self.session.execute(recovered_stmt)).scalar() or 0

        rate = stabilized / total_ever_at_risk if total_ever_at_risk > 0 else 0.0

        return RecoveryMetricDTO(
            recovery_rate=rate,
            stabilized_students=stabilized,
            total_at_risk_students=total_ever_at_risk,
        )

    async def _get_lead_time_metrics(self) -> LeadTimeMetricDTO:
        """Calculate School-wide Lead Time."""
        # Fetch created_at and first_interaction_at for cases that have an interaction
        stmt = select(
            Case.created_at,
            Case.first_interaction_at,
        ).where(Case.first_interaction_at.is_not(None))

        results = (await self.session.execute(stmt)).all()
        total_cases = len(results)

        if total_cases == 0:
            return LeadTimeMetricDTO(
                avg_lead_time_hours=0.0,
                target_hours=TARGET_LEAD_TIME_HOURS,
                within_target_rate=1.0,
            )

        total_hours = 0.0
        within_target = 0
        for created_at, first_interaction_at in results:
            delta = first_interaction_at - created_at
            hours = delta.total_seconds() / 3600.0
            total_hours += hours
            if hours <= TARGET_LEAD_TIME_HOURS:
                within_target += 1

        return LeadTimeMetricDTO(
            avg_lead_time_hours=total_hours / total_cases,
            target_hours=TARGET_LEAD_TIME_HOURS,
            within_target_rate=within_target / total_cases,
        )

    async def _get_nudge_activation_metrics(self) -> NudgeActivationMetricDTO:
        """Calculate Nudge Activation Rate."""
        total_nudges_stmt = select(func.count(InterventionEmail.email_id)).where(
            InterventionEmail.is_nudge.is_(True),
        )
        total_nudges = (await self.session.execute(total_nudges_stmt)).scalar() or 0

        responded_stmt = select(func.count(InterventionEmail.email_id)).where(
            and_(
                InterventionEmail.is_nudge.is_(True),
                InterventionEmail.responded_at.is_not(None),
            ),
        )
        responses = (await self.session.execute(responded_stmt)).scalar() or 0

        rate = responses / total_nudges if total_nudges > 0 else 0.0

        return NudgeActivationMetricDTO(
            activation_rate=rate,
            total_nudges_sent=total_nudges,
            responses_received=responses,
        )

    async def _get_academic_impact_metrics(self) -> AcademicImpactMetricDTO:
        """Calculate Academic Impact Score."""
        stmt = select(
            func.avg(Case.initial_gpa),
            func.avg(Case.final_gpa),
        ).where(
            and_(
                Case.initial_gpa.is_not(None),
                Case.final_gpa.is_not(None),
            ),
        )
        result = (await self.session.execute(stmt)).first()

        avg_before = float(result[0]) if result and result[0] is not None else None
        avg_after = float(result[1]) if result and result[1] is not None else None

        impact = None
        if avg_before is not None and avg_after is not None:
            impact = avg_after - avg_before

        return AcademicImpactMetricDTO(
            avg_gpa_before=avg_before,
            avg_gpa_after=avg_after,
            impact_score=impact,
        )

    async def _get_risk_distribution(self) -> list[RiskDistributionDTO]:
        """Calculate Risk Reason Distribution."""
        total_stmt = select(func.count(Case.case_id))
        total = (await self.session.execute(total_stmt)).scalar() or 1

        stmt = select(
            Case.risk_reason,
            func.count(Case.case_id),
        ).group_by(Case.risk_reason)

        results = (await self.session.execute(stmt)).all()

        return [
            RiskDistributionDTO(
                label=str(row[0]),
                count=row[1],
                percentage=(row[1] / total) * 100.0,
            )
            for row in results
        ]

    async def _get_major_risk_metrics(self) -> list[MajorRiskMetricDTO]:
        """Calculate Major-wise Risk Percentage."""
        # Total students per major
        total_stmt = select(
            Student.major,
            func.count(Student.sid),
        ).group_by(Student.major)
        total_by_major = {
            row[0]: row[1] for row in (await self.session.execute(total_stmt)).all()
        }

        # At-risk students per major
        risk_stmt = (
            select(
                Student.major,
                func.count(Student.sid),
            )
            .where(
                Student.current_risk_status != RiskStatus.NORMAL,
            )
            .group_by(Student.major)
        )
        risk_by_major = {
            row[0]: row[1] for row in (await self.session.execute(risk_stmt)).all()
        }

        all_majors = set(total_by_major.keys()) | set(risk_by_major.keys())

        return [
            MajorRiskMetricDTO(
                major=major,
                total_students=total_by_major.get(major, 0),
                risk_percentage=risk_by_major.get(major, 0) / total_by_major[major]
                if total_by_major.get(major, 0) > 0
                else 0.0,
            )
            for major in all_majors
        ]
