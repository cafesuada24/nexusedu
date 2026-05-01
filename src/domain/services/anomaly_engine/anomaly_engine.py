"""Anomaly engine interface."""

from collections.abc import Mapping, Sequence
from typing import Any, Protocol

from pydantic import UUID4

from src.domain.value_objects.status import RiskStatus


class AnomalyEngine(Protocol):
    """Domain Service for calculating academic performance anomalies."""

    def run(
        self,
        student_data: Mapping[UUID4, Sequence[Mapping[str, int | float]]],
        history_set: set[tuple[UUID4, int, int, int]],
    ) -> tuple[list[dict[str, Any]], dict[UUID4, RiskStatus]]:
        """Calculate anomalies and return results for orchestration.

        Returns:
            A tuple of (new_history_records, student_risk_statuses).
        """
        ...
