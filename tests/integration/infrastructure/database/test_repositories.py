from collections.abc import AsyncGenerator
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.domain.value_objects.status import EmailStatus, InterventionStatus
from src.infrastructure.database.models import Base
from src.infrastructure.persistence.repositories.sqlalchemy_repositories import (
    SqlAlchemyActivityRepository,
    SqlAlchemyAdvisorRepository,
    SqlAlchemyEmailRepository,
    SqlAlchemyIdempotencyRepository,
    SqlAlchemyMetadataRepository,
    SqlAlchemyMetricsRepository,
    SqlAlchemyStudentRepository,
)


@pytest.fixture
async def session() -> AsyncGenerator[AsyncSession]:
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
    sids = [uuid4(), uuid4()]
    students = [
        {'sid': sids[0], 'student_name': 'Alice', 'email': 'a@test.com', 'major': 'CS'},
        {'sid': sids[1], 'student_name': 'Bob', 'email': 'b@test.com', 'major': 'Math'},
    ]
    await repo.ingest_students(students)
    await session.commit()

    # 2. Test Get
    s1 = await repo.get_by_id(sids[0])
    assert s1 is not None
    assert s1.student_name == 'Alice'

    # 3. Test Upsert (Ingest again with same SIDs)
    updated_students = [
        {'sid': sids[0], 'student_name': 'Alice Updated', 'email': 'a@test.com', 'major': 'CS'},
    ]
    await repo.ingest_students(updated_students)
    await session.commit()

    s1_updated = await repo.get_by_id(sids[0])
    assert s1_updated.student_name == 'Alice Updated'  # ingest_students now uses DO UPDATE

@pytest.mark.asyncio
async def test_email_repository(session: AsyncSession) -> None:
    repo = SqlAlchemyEmailRepository(session)
    student_repo = SqlAlchemyStudentRepository(session)

    s1 = uuid4()
    c1 = uuid4()
    # Need to include student_name and email to avoid NOT NULL constraint failure
    await student_repo.ingest_students(
        [{'sid': s1, 'student_name': 'Test Student', 'email': 't@test.com', 'major': 'CS'}],
    )
    await session.commit()

    # Test basic add and get
    from datetime import UTC, datetime

    from src.domain.entities.intervention_email import InterventionEmail as DomainEmail

    email = DomainEmail(
        email_id=uuid4(),
        case_id=c1,
        status=EmailStatus.UNAVAILABLE,
        subject="Sub",
        body="Body",
        created_at=datetime.now(UTC),
    )
    await repo.add(email)
    await session.commit()

    found = await repo.get_by_case(c1)
    assert found.subject == "Sub"


@pytest.mark.asyncio
async def test_idempotency_repository(session: AsyncSession) -> None:
    repo = SqlAlchemyIdempotencyRepository(session)

    key = uuid4()
    assert await repo.check_key(key) is False

    await repo.record_key(key)
    await session.commit()

    assert await repo.check_key(key) is True


@pytest.mark.asyncio
async def test_metadata_repository(session: AsyncSession) -> None:
    repo = SqlAlchemyMetadataRepository(session)

    # 1. List tables
    tables = await repo.list_tables('sis_db')
    assert 'students' in tables
    assert 'advisors' in tables

    # 2. Get table schema
    schema = await repo.get_table_schema('sis_db', 'students')
    assert 'sid' in schema
    assert 'student_name' in schema

    # 3. Execute Raw
    results = await repo.execute_raw('sis_db', 'SELECT 1 as val')
    assert results == [{'val': 1}]


@pytest.mark.asyncio
async def test_advisor_repository_metrics(session: AsyncSession) -> None:
    student_repo = SqlAlchemyStudentRepository(session)
    advisor_repo = SqlAlchemyAdvisorRepository(session)

    # Seed data
    await student_repo.ingest_students(
        [
            {'sid': uuid4(), 'student_name': 'S1', 'email': 's1@test.com', 'major': 'CS'},
            {'sid': uuid4(), 'student_name': 'S2', 'email': 's2@test.com', 'major': 'CS'},
            {'sid': uuid4(), 'student_name': 'S3', 'email': 's3@test.com', 'major': 'Math'},
        ],
    )
    await session.commit()

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
                'sid': uuid4(),
                'student_name': 'Normal Student',
                'email': 'n@test.com',
                'current_risk_status': 'Normal',
            },
            {
                'sid': uuid4(),
                'student_name': 'At Risk Student',
                'email': 'r@test.com',
                'current_risk_status': 'Significant Drop',
            },
        ],
    )
    await session.commit()

    stats = await repo.get_kpi_stats()
    assert stats['total_students'] == 2
    assert stats['retention_rate'] == 50.0
    assert stats['dropout_rate'] == 50.0


@pytest.mark.asyncio
async def test_activity_ingestion(session: AsyncSession) -> None:
    repo = SqlAlchemyActivityRepository(session)

    activities = [
        {
            'sid': uuid4(),
            'course_id': 'C1',
            'score': 90,
            'academic_year': 1,
            'semester': 1,
            'week': 1,
        },
    ]
    await repo.ingest_activities(activities)
    await session.commit()

    avgs = await repo.get_weekly_averages()
    assert len(avgs) == 1
    assert avgs[0]['avg_score'] == 90.0
