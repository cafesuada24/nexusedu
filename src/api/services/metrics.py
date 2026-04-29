"""Service layer for Dashboard Metrics and KPIs."""

from typing import TYPE_CHECKING, Any
from src.telemetry.logger import logger

if TYPE_CHECKING:
    from src.database.manager import DatabaseManager


class MetricsService:
    """Service for calculating system-wide performance metrics."""

    def __init__(self, db_manager: 'DatabaseManager') -> None:
        """Initialize the MetricsService.

        Args:
            db_manager: The database manager instance.
        """
        self.db = db_manager

    def get_kpi_stats(self) -> dict[str, Any]:
        """Calculate high-level KPI stats for the dashboard.

        Returns:
            Dictionary with retention_rate, total_interventions, advisor_engagement, and dropout_rate.
        """
        try:
            # 1. Retention & Dropout (based on risk status)
            # Normal = Retained, Significant Drop = Dropout (approx)
            risk_sql = """
                SELECT 
                    COUNT(*) as total,
                    COUNT(CASE WHEN current_risk_status = 'Normal' THEN 1 END) as normal,
                    COUNT(CASE WHEN current_risk_status LIKE '%Significant Drop%' THEN 1 END) as dropout
                FROM students
            """
            risk_res = self.db.execute('sis_db', risk_sql)[0]
            total = risk_res['total'] or 1
            retention_rate = (risk_res['normal'] / total) * 100
            dropout_rate = (risk_res['dropout'] / total) * 100

            # 2. Interventions
            int_sql = "SELECT COUNT(*) as count FROM students WHERE intervention_status != 'none'"
            int_res = self.db.execute('sis_db', int_sql)[0]

            # 3. Advisor Engagement
            # Percentage of advisors who have at least one entry in the ledger
            adv_sql = """
                SELECT 
                    (SELECT COUNT(DISTINCT advisor_id) FROM advisor_points_ledger) * 100.0 / 
                    NULLIF((SELECT COUNT(*) FROM advisors), 0) as engagement
            """
            adv_res = self.db.execute('sis_db', adv_sql)[0]
            engagement = adv_res['engagement'] or 0.0

            return {
                "retention_rate": round(retention_rate, 1),
                "total_interventions": int_res['count'],
                "advisor_engagement": round(float(engagement), 1),
                "dropout_rate": round(dropout_rate, 1),
                "total_students": total
            }
        except Exception as e:
            logger.error(f"Error calculating KPI stats: {e}")
            raise

    def get_retention_trend(self) -> list[dict[str, Any]]:
        """Retrieve retention trend data over time (weeks).

        Returns:
            List of data points for the trend chart.
        """
        try:
            # We'll use student_status_history to see how many were 'normal' vs total per week
            # We limit to the last 12 weeks for the chart
            sql = """
                SELECT 
                    'W' || week as month, 
                    80 as baseline, -- Hardcoded baseline for comparison
                    COUNT(CASE WHEN anomaly_flag = 'normal' THEN 1 END) * 100.0 / COUNT(*) as current
                FROM student_status_history
                GROUP BY academic_year, semester, week
                ORDER BY academic_year DESC, semester DESC, week DESC
                LIMIT 12
            """
            results = self.db.execute('sis_db', sql)
            # Reverse to get chronological order
            return results[::-1]
        except Exception as e:
            logger.error(f"Error calculating retention trend: {e}")
            raise
