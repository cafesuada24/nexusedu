"""Query service for the Admin Dashboard."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import Float, and_, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dtos.admin_dashboard_dtos import (
    AcademicImpactMetricDTO,
    AdminDashboardDTO,
    LeadTimeMetricDTO,
    MajorRiskMetricDTO,
    NudgeActivationMetricDTO,
    RecoveryMetricDTO,
    RiskDistributionDTO,
)
from src.domain.value_objects.status import (
    InterventionStatus,
    RiskReason,
    RiskStatus,
)
from src.infrastructure.database.models import Case, InterventionEmail, Student

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
        )

    async def _get_recovery_metrics(self) -> RecoveryMetricDTO:
        """Calculate Overall Recovery Rate."""
        # Total unique students ever at-risk (Elevated or Critical)
        # For simplicity in this robust version, we look at current status
        # but in production, we would join with student_status_history.
        total_stmt = select(func.count(Student.sid)).where(
            Student.current_risk_status != RiskStatus.NORMAL,
        )
        total_at_risk = (await self.session.execute(total_stmt)).scalar() or 0

        # Students recovered: previously at risk (has a case) and now NORMAL
        recovered_stmt = select(func.count(func.distinct(Case.sid))).join(
            Student,
            Case.sid == Student.sid,
        ).where(
            and_(
                Student.current_risk_status == RiskStatus.NORMAL,
                Case.intervention_status == InterventionStatus.RESOLVED,
            ),
        )
        stabilized = (await self.session.execute(recovered_stmt)).scalar() or 0

        rate = stabilized / total_at_risk if total_at_risk > 0 else 0.0

        return RecoveryMetricDTO(
            recovery_rate=rate,
            stabilized_students=stabilized,
            total_at_risk_students=total_at_risk,
        )

    async def _get_lead_time_metrics(self) -> LeadTimeMetricDTO:
        """Calculate School-wide Lead Time."""
        # AVG(first_interaction_at - created_at)
        diff = func.extract('epoch', Case.first_interaction_at - Case.created_at) / 3600.0
        stmt = select(
            func.avg(diff),
            func.count(Case.case_id),
        ).where(Case.first_interaction_at.is_not(None))

        result = (await self.session.execute(stmt)).first()
        avg_hours = float(result[0]) if result and result[0] is not None else 0.0
        total_cases = result[1] if result else 0

        # Within target (4h)
        target_stmt = select(func.count(Case.case_id)).where(
            and_(
                Case.first_interaction_at.is_not(None),
                diff <= TARGET_LEAD_TIME_HOURS,
            ),
        )
        within_target = (await self.session.execute(target_stmt)).scalar() or 0
        rate = within_target / total_cases if total_cases > 0 else 1.0

        return LeadTimeMetricDTO(
            avg_lead_time_hours=avg_hours,
            target_hours=TARGET_LEAD_TIME_HOURS,
            within_target_rate=rate,
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
                reason=str(row[0]),
                count=row[1],
                percentage=row[1] / total,
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
        total_by_major = {row[0]: row[1] for row in (await self.session.execute(total_stmt)).all()}

        # At-risk students per major
        risk_stmt = select(
            Student.major,
            func.count(Student.sid),
        ).where(
            Student.current_risk_status != RiskStatus.NORMAL,
        ).group_by(Student.major)
        risk_by_major = {row[0]: row[1] for row in (await self.session.execute(risk_stmt)).all()}

        all_majors = set(total_by_major.keys()) | set(risk_by_major.keys())

        return [
            MajorRiskMetricDTO(
                major=major,
                total_students=total_by_major.get(major, 0),
                risk_percentage=risk_by_major.get(major, 0) / total_by_major[major] if total_by_major.get(major, 0) > 0 else 0.0,
            )
            for major in all_majors
        ]
