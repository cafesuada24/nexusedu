"""Shared pytest fixtures for API and Database tests."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from src.api.dependencies.agent import get_agent
from src.api.main import app
from src.database.algorithms.zscore import DuckDBZScoreAnomalyAlgorithm
from src.database.engines.duckdb_engine import DuckDBEngine
from src.database.manager import DatabaseManager

if TYPE_CHECKING:
    from collections.abc import Generator
    from pathlib import Path

    from src.database.interfaces import AnomalyAlgorithm, DatabaseEngine

@pytest.fixture
def test_data_dir(tmp_path: Path) -> Path:
    """Provides a temporary directory for test database files."""
    return tmp_path

@pytest.fixture
def test_db_manager(test_data_dir: Path) -> DatabaseManager:
    """Provides a DatabaseManager instance configured for testing."""
    engine = DuckDBEngine(data_dir=test_data_dir)
    algo = DuckDBZScoreAnomalyAlgorithm()
    manager = DatabaseManager()
    manager.initialize(engine=engine, anomaly_algo=algo)
    manager.initialize_schema()
    return manager

@pytest.fixture(autouse=True)
def patch_db_manager(
    monkeypatch: pytest.MonkeyPatch, test_db_manager: DatabaseManager
) -> None:
    """Monkeypatches the global db_manager to use the test version during tests."""
    monkeypatch.setattr('src.database.db_manager', test_db_manager)
    monkeypatch.setattr('src.database.manager.db_manager', test_db_manager)
    monkeypatch.setattr('src.tools.db.db_manager', test_db_manager)
    monkeypatch.setattr('src.api.routes.data.db_manager', test_db_manager)
    monkeypatch.setattr('src.api.routes.alerts.db_manager', test_db_manager)

@pytest.fixture
def mock_agent() -> MagicMock:
    """Provides a MagicMock for the LangGraph agent."""
    agent = MagicMock()
    # Mock ainvoke to return a simple message list
    agent.ainvoke = AsyncMock(
        return_value={
            'messages': [
                MagicMock(content='Hello {{STUDENT_NAME}}, this is an AI draft.'),
            ],
        }
    )
    return agent

@pytest.fixture
def client(mock_agent: MagicMock) -> Generator[TestClient, None, None]:
    """Provides a FastAPI TestClient with mocked dependencies."""
    app.dependency_overrides[get_agent] = lambda: mock_agent

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()
