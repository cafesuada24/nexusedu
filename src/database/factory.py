"""Factory and registry for database engines and anomaly algorithms."""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from src.database.algorithms.zscore import DuckDBZScoreAnomalyAlgorithm
from src.database.engines.duckdb_engine import DuckDBEngine
from src.database.interfaces import AnomalyAlgorithm, DatabaseEngine

T = TypeVar('T')

class Registry(dict[str, Callable[[], T]]):
    """Generic registry for components."""

    def register(self, name: str, factory: Callable[[], T]) -> None:
        """Register a component factory."""
        self[name] = factory

    def create(self, name: str) -> T:
        """Create a component instance by name."""
        if name not in self:
            msg = f"No component registered for name: '{name}'"
            raise ValueError(msg)
        return self[name]()

# Registries
engine_registry = Registry[DatabaseEngine]()
algorithm_registry = Registry[AnomalyAlgorithm]()

# Register defaults
engine_registry.register('duckdb', DuckDBEngine)
algorithm_registry.register('zscore', DuckDBZScoreAnomalyAlgorithm)
