"""Z-Score anomaly detection algorithm optimized for DuckDB."""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING, override

from src.database.engines.duckdb_engine import DuckDBEngine

if TYPE_CHECKING:
    from src.database.interfaces import DatabaseEngine

class DuckDBZScoreAnomalyAlgorithm:
    """Z-Score anomaly detection algorithm optimized for DuckDB."""

    def run(self, engine: DatabaseEngine) -> None:
        """Calculate baselines and anomalies, updating the history table."""
        if not isinstance(engine, DuckDBEngine):
            msg = 'DuckDBZScoreAnomalyAlgorithm requires DuckDBEngine'
            raise TypeError(msg)

        # sis_db and lms_db are already attached to the engine's main connection.
        # _get_connection('sis_db') returns a cursor set to sis_db context.
        with engine.write_lock, engine.get_connection('sis_db') as cursor:
            cursor.begin()
            try:
                # 1. Calculate and insert new history records
                # Refer to lms_db explicitly for the activities table
                cursor.execute("""
                    INSERT INTO student_status_history (
                        history_id, sid, academic_year, semester,
                        baseline_avg, baseline_std, current_score_avg, z_score, anomaly_flag
                    )
                    WITH semester_stats AS (
                        SELECT
                            sid,
                            academic_year,
                            semester,
                            AVG(score) as avg_score
                        FROM lms_db.activities
                        GROUP BY sid, academic_year, semester
                    ),
                    historical_stats AS (
                        SELECT
                            sid,
                            academic_year,
                            semester,
                            avg_score,
                            AVG(avg_score) OVER (
                                PARTITION BY sid
                                ORDER BY academic_year, semester
                                ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
                            ) as baseline_avg,
                            STDDEV(avg_score) OVER (
                                PARTITION BY sid
                                ORDER BY academic_year, semester
                                ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
                            ) as baseline_std
                        FROM semester_stats
                    )
                    SELECT
                        uuid() as history_id,
                        sid,
                        academic_year,
                        semester,
                        baseline_avg,
                        baseline_std,
                        avg_score as current_score_avg,
                        (avg_score - baseline_avg) / NULLIF(baseline_std, 0) as z_score,
                        CASE
                            WHEN (avg_score - baseline_avg) / NULLIF(baseline_std, 0) < -1.5 THEN 'Significant Drop'
                            WHEN avg_score < baseline_avg * 0.7 THEN 'Critical Drop'
                            ELSE 'Normal'
                        END as anomaly_flag
                    FROM historical_stats
                    WHERE baseline_avg IS NOT NULL
                    AND (sid, academic_year, semester) NOT IN (SELECT sid, academic_year, semester FROM student_status_history);
                """)

                # 2. Update current risk and intervention status in students table
                cursor.execute("""
                    UPDATE students
                    SET
                        current_risk_status = h.anomaly_flag,
                        intervention_status = CASE
                            WHEN h.anomaly_flag != 'Normal' AND intervention_status IN ('none', 'resolved', 'expired')
                            THEN 'new'
                            ELSE intervention_status
                        END
                    FROM (
                        SELECT sid, anomaly_flag
                        FROM student_status_history
                        QUALIFY ROW_NUMBER() OVER (PARTITION BY sid ORDER BY academic_year DESC, semester DESC) = 1
                    ) h
                    WHERE students.sid = h.sid;
                """)

                cursor.commit()
            except Exception:
                cursor.rollback()
                raise
