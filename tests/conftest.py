"""Shared pytest fixtures for API and Database tests."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.adapters.database.sqlalchemy_repositories import (
    SqlAlchemyActivityRepository,
    SqlAlchemyAdvisorRepository,
    SqlAlchemyAlertRepository,
    SqlAlchemyEmailRepository,
    SqlAlchemyIdempotencyRepository,
    SqlAlchemyMetricsRepository,
    SqlAlchemyStatusHistoryRepository,
    SqlAlchemyStudentRepository,
    SqlAlchemyMetadataRepository,
)
from src.api.auth import User, UserRole, current_active_user
from src.api.lifecycle import (
    get_advisor_repository,
    get_agent,
    get_alert_service,
    get_data_service,
    get_jobs_store,
    get_metrics_repository,
    get_metrics_service,
    get_query_service,
    get_status_history_repository,
    get_student_repository,
    get_metadata_repository,
)
from src.api.main import app
from src.api.models.response import JobStatusResponse
from src.database.models import Base
from src.database.session import get_async_session
from src.utils.collections import BoundedDict

if TYPE_CHECKING:
    from collections.abc import Generator

    from src.domain.ports.repositories import (
        ActivityRepository,
        AdvisorRepository,
        AlertRepository,
        MetricsRepository,
        StatusHistoryRepository,
        StudentRepository,
        MetadataRepository,
        EmailRepository,
        IdempotencyRepository,
    )


@pytest.fixture(autouse=True)
def mock_baml(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Mock BAML client to avoid live LLM calls during tests."""
    mock_b = MagicMock()
    mock_b.Respond.return_value = "OK"
    mock_b.GenerateDraftEmail = AsyncMock(return_value="AI Draft content")
    mock_b.GenerateSQL.return_value = MagicMock(sql="SELECT 1")
    
    monkeypatch.setattr('src.api.routes.health.b', mock_b)
    monkeypatch.setattr('src.api.services.alerts.b_async', mock_b) # In alerts it is b_async
    monkeypatch.setattr('src.agents.nodes.sql_worker.b', mock_b)
    return mock_b


@pytest.fixture(autouse=True)
def mock_arq_pool(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Mock ARQ Redis pool creation."""
    mock_pool = AsyncMock()
    mock_pool.enqueue_job = AsyncMock(return_value=MagicMock(job_id="test_job_id"))
    
    monkeypatch.setattr(
        'src.api.lifecycle.create_pool',
        AsyncMock(return_value=mock_pool),
    )
    return mock_pool


@pytest.fixture
def mock_agent() -> MagicMock:
    """Provides a MagicMock for the LangGraph agent."""
    agent = MagicMock()
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
async def test_db_session():
    """Provides an in-memory SQLite session for testing."""
    engine = create_async_engine('sqlite+aiosqlite:///:memory:')
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as session:
        yield session

    await engine.dispose()


@pytest.fixture
def student_repository(test_db_session: AsyncSession) -> StudentRepository:
    """Provides a SqlAlchemyStudentRepository."""
    return SqlAlchemyStudentRepository(test_db_session)


@pytest.fixture
def advisor_repository(test_db_session: AsyncSession) -> AdvisorRepository:
    """Provides a SqlAlchemyAdvisorRepository."""
    return SqlAlchemyAdvisorRepository(test_db_session)


@pytest.fixture
def alert_repository(test_db_session: AsyncSession) -> AlertRepository:
    """Provides a SqlAlchemyAlertRepository."""
    return SqlAlchemyAlertRepository(test_db_session)


@pytest.fixture
def metrics_repository(test_db_session: AsyncSession) -> MetricsRepository:
    """Provides a SqlAlchemyMetricsRepository."""
    return SqlAlchemyMetricsRepository(test_db_session)


@pytest.fixture
def activity_repository(test_db_session: AsyncSession) -> ActivityRepository:
    """Provides a SqlAlchemyActivityRepository."""
    return SqlAlchemyActivityRepository(test_db_session)


@pytest.fixture
def status_history_repository(test_db_session: AsyncSession) -> StatusHistoryRepository:
    """Provides a SqlAlchemyStatusHistoryRepository."""
    return SqlAlchemyStatusHistoryRepository(test_db_session)

@pytest.fixture
def metadata_repository(test_db_session: AsyncSession) -> MetadataRepository:
    """Provides a SqlAlchemyMetadataRepository."""
    return SqlAlchemyMetadataRepository(test_db_session)

@pytest.fixture
def email_repository(test_db_session: AsyncSession) -> EmailRepository:
    """Provides a SqlAlchemyEmailRepository."""
    return SqlAlchemyEmailRepository(test_db_session)

@pytest.fixture
def idempotency_repository(test_db_session: AsyncSession) -> IdempotencyRepository:
    """Provides a SqlAlchemyIdempotencyRepository."""
    return SqlAlchemyIdempotencyRepository(test_db_session)


@pytest.fixture
def client(
    mock_agent: MagicMock,
    mock_user: User,
    test_db_session: AsyncSession,
) -> Generator[TestClient, None, None]:
    """Provides a FastAPI TestClient with mocked dependencies."""
    test_jobs = BoundedDict[str, JobStatusResponse](maxsize=100)

    app.dependency_overrides[get_agent] = lambda: mock_agent
    app.dependency_overrides[get_jobs_store] = lambda: test_jobs
    app.dependency_overrides[current_active_user] = lambda: mock_user
    app.dependency_overrides[get_async_session] = lambda: test_db_session

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()
