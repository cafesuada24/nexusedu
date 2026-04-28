"""Shared pytest fixtures for API and Database tests."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from src.api.auth import User, current_active_user
from src.api.lifecycle import get_agent, get_dbmanager
from src.api.main import app
from src.database.algorithms.zscore import DuckDBZScoreAnomalyAlgorithm
from src.database.engines.duckdb_engine import DuckDBEngine
from src.database.manager import DatabaseManager

if TYPE_CHECKING:
    from collections.abc import Generator
    from pathlib import Path


@pytest.fixture(autouse=True)
def disable_motherduck(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure MotherDuck is disabled during tests."""
    monkeypatch.delenv('MOTHERDUCK_TOKEN', raising=False)


@pytest.fixture
def test_data_dir(tmp_path: Path) -> Path:
    """Provides a temporary directory for test database files."""
    return tmp_path


@pytest.fixture
def test_db_manager(test_data_dir: Path) -> DatabaseManager:
    """Provides a DatabaseManager instance configured for testing."""
    print(f'DEBUG: test_db_manager using data_dir={test_data_dir}')
    engine = DuckDBEngine(data_dir=test_data_dir)
    algo = DuckDBZScoreAnomalyAlgorithm()
    manager = DatabaseManager()
    manager.initialize(engine=engine, anomaly_algo=algo)
    manager.initialize_schema()
    return manager


@pytest.fixture(autouse=True)
def patch_db_manager(
    monkeypatch: pytest.MonkeyPatch,
    test_db_manager: DatabaseManager,
) -> None:
    """Monkeypatches the global db_manager to use the test version during tests."""
    monkeypatch.setattr('src.api.lifecycle.get_dbmanager', lambda: test_db_manager)


@pytest.fixture
def mock_agent() -> MagicMock:
    """Provides a MagicMock for the LangGraph agent."""
    agent = MagicMock()
    # Mock ainvoke to return a simple message list
    agent.ainvoke = AsyncMock(
        return_value={
            'messages': [
                {
                    'role': 'assistant',
                    'content': 'Hello {{STUDENT_NAME}}, this is an AI draft.',
                },
            ],
        },
    )
    return agent


@pytest.fixture
def mock_user() -> User:
    """Provides a mock authenticated User with admin:all role."""
    return User(
        id=uuid.uuid4(),
        email='test@example.com',
        hashed_password='hashed_password',
        role='admin:all',
        is_active=True,
        is_superuser=False,
        is_verified=True,
    )


@pytest.fixture
def client(
    mock_agent: MagicMock, test_db_manager: DatabaseManager, mock_user: User
) -> Generator[TestClient, None, None]:
    """Provides a FastAPI TestClient with mocked dependencies."""
    app.dependency_overrides[get_agent] = lambda: mock_agent
    app.dependency_overrides[get_dbmanager] = lambda: test_db_manager
    app.dependency_overrides[current_active_user] = lambda: mock_user

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()

