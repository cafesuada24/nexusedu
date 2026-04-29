"""Shared pytest fixtures for API and Database tests."""

from __future__ import annotations

import os
import uuid
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

# Ensure DuckDB instances created by TestClient are isolated and don't conflict with real data
os.environ['DB_DIR'] = '/tmp/pytest_duckdb'
os.environ['AUTH_DB_URL'] = 'sqlite+aiosqlite:///:memory:'
os.makedirs('/tmp/pytest_duckdb', exist_ok=True)

from src.api.auth import User, UserRole, current_active_user
from src.api.lifecycle import (
    get_agent,
    get_alert_service,
    get_data_service,
    get_dbmanager,
    get_jobs_store,
    get_metrics_service,
    get_query_service,
)
from src.api.main import app
from src.api.models.response import JobStatusResponse
from src.api.services.alerts import AlertService
from src.api.services.data import DataService
from src.api.services.gamification import GamificationService
from src.api.services.metrics import MetricsService
from src.api.services.query import QueryService
from src.database.algorithms.zscore import DuckDBZScoreAnomalyAlgorithm
from src.database.engines.duckdb_engine import DuckDBEngine
from src.database.manager import DatabaseManager
from src.database.repositories.advisor_repository import AdvisorRepository
from src.database.repositories.student_repository import StudentRepository
from src.types import BoundedDict

if TYPE_CHECKING:
    from collections.abc import Generator
    from pathlib import Path


@pytest.fixture(autouse=True)
def disable_motherduck(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure MotherDuck is disabled during tests."""
    monkeypatch.delenv('MOTHERDUCK_TOKEN', raising=False)


@pytest.fixture(autouse=True)
def mock_arq_pool(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mock ARQ Redis pool creation to avoid connection errors in tests."""
    mock_pool = AsyncMock()

    async def mock_enqueue_job(func_name: str, *args, **kwargs) -> Any:
        """Mock enqueue_job that executes tasks synchronously using the app's service instances."""
        from src.api.main import app
        # Ensure app_state is initialized (TestClient does this on first request)
        if not hasattr(app.state, 'app_state'):
            return AsyncMock()
            
        state = app.state.app_state

        if func_name == 'run_email_draft_task':
            await state.alert_service.run_email_draft_task(*args, **kwargs)
        elif func_name == 'run_agent_task':
            await state.query_service.run_agent_task(*args, **kwargs)

        return AsyncMock()

    mock_pool.enqueue_job = AsyncMock(side_effect=mock_enqueue_job)
    monkeypatch.setattr(
        'src.api.lifecycle.create_pool', AsyncMock(return_value=mock_pool)
    )


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
    """Provides a mock authenticated User with admin role."""
    return User(
        id=uuid.uuid4(),
        email='test@example.com',
        hashed_password='hashed_password',
        role=UserRole.ADMIN.value,
        is_active=True,
        is_superuser=False,
        is_verified=True,
    )


@pytest.fixture
def client(
    mock_agent: MagicMock, test_db_manager: DatabaseManager, mock_user: User
) -> Generator[TestClient, None, None]:
    """Provides a FastAPI TestClient with mocked dependencies."""
    test_jobs = BoundedDict[str, JobStatusResponse](maxsize=100)
    app.dependency_overrides[get_agent] = lambda: mock_agent
    app.dependency_overrides[get_dbmanager] = lambda: test_db_manager
    app.dependency_overrides[get_jobs_store] = lambda: test_jobs
    app.dependency_overrides[current_active_user] = lambda: mock_user

    # Provide real services initialized with the test_db_manager
    advisor_repo = AdvisorRepository(test_db_manager)
    student_repo = StudentRepository(test_db_manager)
    gamification_service = GamificationService(advisor_repo, student_repo)
    alert_service = AlertService(test_db_manager, gamification_service, student_repo)
    query_service = QueryService(mock_agent, test_db_manager)
    data_service = DataService(test_db_manager)
    metrics_service = MetricsService(test_db_manager)

    app.dependency_overrides[get_alert_service] = lambda: alert_service
    app.dependency_overrides[get_query_service] = lambda: query_service
    app.dependency_overrides[get_data_service] = lambda: data_service
    app.dependency_overrides[get_metrics_service] = lambda: metrics_service

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()
