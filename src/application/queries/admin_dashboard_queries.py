"""Query service for the Admin Dashboard."""

from sqlalchemy import and_, case, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dtos.admin_dashboard_dtos import (
    AcademicImpactMetricDTO,
    AdminDashboardDTO,
    AdvisorAdminMetricRowDTO,
    AdvisorAdminMetricsResponseDTO,
    CriticalCaseDTO,
    LeadTimeMetricDTO,
    MajorRiskMetricDTO,
    NudgeActivationMetricDTO,
    RecoveryMetricDTO,
    RiskDistributionDTO,
    SystemicRiskMetricDTO,
    TrendDistributionDTO,
)
from src.domain.value_objects.status import (
    EmailStatus,
    InterventionStatus,
    RiskStatus,
)
from src.infrastructure.database.models import (
    Advisor,
    Appointment,
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

    async def get_advisor_performance_metrics(self) -> AdvisorAdminMetricsResponseDTO:
        """Fetch performance metrics for all advisors."""
        # 1. Get all advisors
        advisors_stmt = select(Advisor).order_by(Advisor.name)
        advisors = (await self.session.execute(advisors_stmt)).scalars().all()

        # 2. Get all cases with relevant data for metrics
        cases_stmt = (
            select(
                Case.case_id,
                Case.assigned_advisor_id,
                Case.intervention_status,
                Case.created_at,
                Case.closed_at,
                Case.first_interaction_at,
                Appointment.duration_minutes,
                Student.sid,
                Student.current_risk_status,
                InterventionEmail.status.label('email_status'),
                Appointment.appointment_id,
            )
            .select_from(Case)
            .outerjoin(Student, Case.sid == Student.sid)
            .outerjoin(Appointment, Case.case_id == Appointment.case_id)
            .outerjoin(InterventionEmail, Case.case_id == InterventionEmail.case_id)
            .where(Case.assigned_advisor_id.is_not(None))
        )
        case_data = (await self.session.execute(cases_stmt)).all()

        # 3. Aggregate in Python for database-agnostic calculations
        metrics_map = {
            adv.advisor_id: {
                'active_cases': 0,
                'total_cases': 0,
                'resolution_seconds': [],
                'lead_time_seconds': [],
                'meeting_minutes': 0.0,
                'recovered_students': set(),
                'total_students': set(),
                'outreach_success_cases': set(),
                'outreach_attempt_cases': set(),
            }
            for adv in advisors
        }

        for row in case_data:
            adv_id = row.assigned_advisor_id
            if adv_id not in metrics_map:
                continue

            stats = metrics_map[adv_id]
            stats['total_cases'] += 1
            if row.intervention_status not in (
                InterventionStatus.RESOLVED,
                InterventionStatus.FAILED,
                InterventionStatus.DISMISSED,
            ):
                stats['active_cases'] += 1

            # Resolution Time
            if row.closed_at and row.created_at:
                delta = row.closed_at - row.created_at
                stats['resolution_seconds'].append(delta.total_seconds())

            # Lead Time
            if row.first_interaction_at and row.created_at:
                delta = row.first_interaction_at - row.created_at
                stats['lead_time_seconds'].append(delta.total_seconds())

            # Meeting Minutes
            if row.duration_minutes:
                stats['meeting_minutes'] += float(row.duration_minutes)

            # Recovery and Total Students
            if row.sid:
                stats['total_students'].add(row.sid)
                if row.current_risk_status == RiskStatus.NORMAL:
                    stats['recovered_students'].add(row.sid)

            # Outreach Effectiveness
            if row.email_status == EmailStatus.SENT:
                stats['outreach_attempt_cases'].add(row.case_id)
                if row.appointment_id:
                    stats['outreach_success_cases'].add(row.case_id)

        # 4. Convert to DTOs
        rows = []
        for adv in advisors:
            stats = metrics_map[adv.advisor_id]

            avg_res_days = None
            if stats['resolution_seconds']:
                avg_res_days = (
                    sum(stats['resolution_seconds']) / len(stats['resolution_seconds'])
                ) / 86400.0

            avg_lead_hours = None
            if stats['lead_time_seconds']:
                avg_lead_hours = (
                    sum(stats['lead_time_seconds']) / len(stats['lead_time_seconds'])
                ) / 3600.0

            recovery_rate = 0.0
            if stats['total_students']:
                recovery_rate = len(stats['recovered_students']) / len(
                    stats['total_students'],
                )

            outreach_rate = 0.0
            if stats['outreach_attempt_cases']:
                outreach_rate = len(stats['outreach_success_cases']) / len(
                    stats['outreach_attempt_cases'],
                )

            rows.append(
                AdvisorAdminMetricRowDTO(
                    advisor_id=adv.advisor_id,
                    name=adv.name,
                    faculty=adv.faculty,
                    active_cases=stats['active_cases'],
                    total_cases=stats['total_cases'],
                    avg_resolution_days=avg_res_days,
                    avg_lead_time_hours=avg_lead_hours,
                    meeting_hours=stats['meeting_minutes'] / 60.0,
                    outreach_success_rate=outreach_rate,
                    recovery_rate=recovery_rate,
                ),
            )

        return AdvisorAdminMetricsResponseDTO(advisors=rows)

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
            critical_cases=await self._get_critical_cases(),
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

    async def _get_critical_cases(self) -> list[CriticalCaseDTO]:
        """Fetch high-priority cases requiring leadership attention."""
        # Selection criteria:
        # 1. Critical risk status
        # 2. OR systemic breadth > 0.8
        # 3. OR unassigned/unaccepted cases older than 24 hours

        from datetime import datetime, timedelta, UTC

        threshold_24h = datetime.now(UTC) - timedelta(hours=24)

        # Get latest systemic breadth per student
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

        stmt = (
            select(
                Case.case_id,
                Student.student_name,
                Student.major,
                Case.risk_reason,
                Student.current_risk_status,
                latest_history_subq.c.systemic_breadth,
            )
            .join(Student, Case.sid == Student.sid)
            .outerjoin(latest_history_subq, Student.sid == latest_history_subq.c.sid)
            .where(
                and_(
                    Case.intervention_status != InterventionStatus.RESOLVED,
                    Case.intervention_status != InterventionStatus.DISMISSED,
                    latest_history_subq.c.rn == 1,
                    func.or_(
                        Student.current_risk_status == RiskStatus.CRITICAL,
                        latest_history_subq.c.systemic_breadth > 0.8,
                        and_(
                            Case.intervention_status == InterventionStatus.NEW,
                            Case.created_at < threshold_24h,
                        ),
                    ),
                )
            )
            .order_by(desc(latest_history_subq.c.systemic_breadth), Case.created_at)
            .limit(5)
        )

        results = (await self.session.execute(stmt)).all()

        return [
            CriticalCaseDTO(
                case_id=row[0],
                student_name=row[1],
                major=row[2],
                risk_reason=str(row[3]),
                priority='high'
                if row[4] == RiskStatus.CRITICAL or (row[5] or 0) > 0.9
                else 'medium',
                breadth_score=float(row[5]) if row[5] is not None else None,
            )
            for row in results
        ]
