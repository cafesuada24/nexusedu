import time
import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.adapters.database.sqlalchemy_repositories import (
    SqlAlchemyActivityRepository,
    SqlAlchemyAdvisorRepository,
    SqlAlchemyMetricsRepository,
    SqlAlchemyStudentRepository,
)
from src.database.models import Activity, Advisor, Base, Student, StudentStatusHistory


@pytest.fixture
async def session():
    """Provides an in-memory SQLite session for testing."""
    engine = create_async_engine('sqlite+aiosqlite:///:memory:')
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_student_repository(session: AsyncSession) -> None:
    repo = SqlAlchemyStudentRepository(session)

    # 1. Test Ingest
    students = [
        {'sid': 'S1', 'student_name': 'Alice', 'email': 'a@test.com', 'major': 'CS'},
        {'sid': 'S2', 'student_name': 'Bob', 'email': 'b@test.com', 'major': 'Math'},
    ]
    await repo.ingest_students(students)

    # 2. Test Get
    s1 = await repo.get_by_id('S1')
    assert s1 is not None
    assert s1.student_name == 'Alice'

    # 3. Test PII
    pii = await repo.get_pii('S2')
    assert pii['student_name'] == 'Bob'
    assert pii['email'] == 'b@test.com'

    # 4. Test Update Status
    await repo.update_intervention_status('S1', 'sent')
    s1_updated = await repo.get_by_id('S1')
    assert s1_updated.intervention_status == 'sent'


@pytest.mark.asyncio
async def test_advisor_repository_metrics(session: AsyncSession) -> None:
    student_repo = SqlAlchemyStudentRepository(session)
    advisor_repo = SqlAlchemyAdvisorRepository(session)

    # Seed data
    await student_repo.ingest_students(
        [
            {'sid': 'S1', 'major': 'CS', 'intervention_status': 'sent'},
            {'sid': 'S2', 'major': 'CS', 'intervention_status': 'new'},
            {'sid': 'S3', 'major': 'Math', 'intervention_status': 'none'},
        ]
    )

    metrics = await advisor_repo.get_engagement_metrics()
    # Ordered by 'sent' DESC
    assert metrics[0]['faculty'] == 'CS'
    assert metrics[0]['sent'] == 1
    assert metrics[0]['drafted'] == 1

    assert metrics[1]['faculty'] == 'Math'
    assert metrics[1]['sent'] == 0


@pytest.mark.asyncio
async def test_metrics_repository(session: AsyncSession) -> None:
    repo = SqlAlchemyMetricsRepository(session)
    student_repo = SqlAlchemyStudentRepository(session)

    await student_repo.ingest_students(
        [
            {
                'sid': 'S1',
                'current_risk_status': 'Normal',
                'intervention_status': 'none',
            },
            {
                'sid': 'S2',
                'current_risk_status': 'Significant Drop',
                'intervention_status': 'new',
            },
        ]
    )

    stats = await repo.get_kpi_stats()
    assert stats['total_students'] == 2
    assert stats['retention_rate'] == 50.0
    assert stats['dropout_rate'] == 50.0


@pytest.mark.asyncio
async def test_activity_ingestion(session: AsyncSession) -> None:
    repo = SqlAlchemyActivityRepository(session)

    activities = [
        {
            'sid': 'S1',
            'course_id': 'C1',
            'score': 90,
            'academic_year': 1,
            'semester': 1,
            'week': 1,
        },
    ]
    await repo.ingest_activities(activities)

    avgs = await repo.get_weekly_averages()
    assert len(avgs) == 1
    assert avgs[0]['avg_score'] == 90.0
