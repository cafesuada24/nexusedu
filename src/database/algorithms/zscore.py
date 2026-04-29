"""Z-Score anomaly detection algorithm optimized for DuckDB."""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING, override

from duckdb import DatabaseError

from src.database.engines.duckdb_engine import DuckDBEngine

if TYPE_CHECKING:
    from src.database.interfaces import DatabaseEngine

class DuckDBZScoreAnomalyAlgorithm:
    """Z-Score anomaly detection algorithm optimized for DuckDB."""

    def run(self, engine: DatabaseEngine) -> list[str]:
        """Calculate baselines and anomalies, updating the history table.

        Returns:
            List of student IDs (SIDs) whose status transitioned to 'new'.
        """
        if not isinstance(engine, DuckDBEngine):
            msg = 'DuckDBZScoreAnomalyAlgorithm requires DuckDBEngine'
            raise TypeError(msg)

        # sis_db and lms_db are already attached to the engine's main connection.
        # _get_cursor('sis_db') returns a cursor set to sis_db context.
        with engine.write_lock, engine.get_cursor('sis_db') as cursor:
            cursor.begin()
            try:
                # 1. Calculate and insert new history records
                # ... (rest of query remains same)
                cursor.execute("""
                    INSERT INTO student_status_history (
                        history_id, sid, academic_year, semester, week,
                        baseline_avg, baseline_std, current_score_avg, z_score, anomaly_flag
                    )
                    WITH weekly_stats AS (
                        SELECT
                            sid,
                            academic_year,
                            semester,
                            week,
                            AVG(score) as avg_score
                        FROM lms_db.activities
                        GROUP BY sid, academic_year, semester, week
                    ),
                    historical_stats AS (
                        SELECT
                            sid,
                            academic_year,
                            semester,
                            week,
                            avg_score,
                            AVG(avg_score) OVER (
                                PARTITION BY sid
                                ORDER BY academic_year, semester, week
                                ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
                            ) as baseline_avg,
                            STDDEV(avg_score) OVER (
                                PARTITION BY sid
                                ORDER BY academic_year, semester, week
                                ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
                            ) as baseline_std
                        FROM weekly_stats
                    )
                    SELECT
                        uuid() as history_id,
                        sid,
                        academic_year,
                        semester,
                        week,
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
                    AND (sid, academic_year, semester, week) NOT IN (SELECT sid, academic_year, semester, week FROM student_status_history);
                """)

                # 2. Identify students who will transition to 'new'
                newly_at_risk_query = """
                    SELECT students.sid
                    FROM students
                    JOIN (
                        SELECT sid, anomaly_flag
                        FROM student_status_history
                        QUALIFY ROW_NUMBER() OVER (PARTITION BY sid ORDER BY academic_year DESC, semester DESC, week DESC) = 1
                    ) h ON students.sid = h.sid
                    WHERE h.anomaly_flag != 'Normal' 
                    AND students.intervention_status IN ('none', 'resolved', 'expired')
                """
                new_sids = [r[0] for r in cursor.execute(newly_at_risk_query).fetchall()]

                # 3. Update current risk and intervention status in students table
                cursor.execute("""
                    UPDATE students
                    SET
                        current_risk_status = h.anomaly_flag,
                        intervention_status = 'new'
                    FROM (
                        SELECT sid, anomaly_flag
                        FROM student_status_history
                        QUALIFY ROW_NUMBER() OVER (PARTITION BY sid ORDER BY academic_year DESC, semester DESC, week DESC) = 1
                    ) h
                    WHERE students.sid = h.sid
                    AND h.anomaly_flag != 'Normal'
                    AND intervention_status IN ('none', 'resolved', 'expired');

                    UPDATE students
                    SET
                        current_risk_status = h.anomaly_flag
                    FROM (
                        SELECT sid, anomaly_flag
                        FROM student_status_history
                        QUALIFY ROW_NUMBER() OVER (PARTITION BY sid ORDER BY academic_year DESC, semester DESC, week DESC) = 1
                    ) h
                    WHERE students.sid = h.sid
                    AND (h.anomaly_flag = 'Normal' OR intervention_status NOT IN ('none', 'resolved', 'expired'));
                """)

                cursor.commit()
                return new_sids
            except DatabaseError:
                raise
            except Exception:
                cursor.rollback()
                raise
