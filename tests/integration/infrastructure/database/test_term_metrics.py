import pytest
import uuid
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from src.infrastructure.database.models import Base, Activity
from src.infrastructure.persistence.repositories.sqlalchemy_repositories import SqlAlchemyActivityRepository
from src.infrastructure.persistence.query_services.student_query_service import SqlAlchemyStudentQueryService
from sqlalchemy import select

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
async def test_deterministic_upsert(session: AsyncSession):
    repo = SqlAlchemyActivityRepository(session)
    sid = uuid.uuid4()
    
    # 1. First Ingestion
    activities = [
        {
            'sid': sid,
            'course_id': 'CS101',
            'course_name': 'Introduction to Computer Science',
            'test_type': 'Final',
            'score': 80,
            'academic_year': 2023,
            'semester': 1,
            'week': 16,
        }
    ]
    await repo.ingest_activities(activities)
    await session.commit()
    
    # Verify count
    res = await session.execute(select(Activity))
    all_activities = res.all()
    assert len(all_activities) == 1
    first_id = all_activities[0][0].activity_id
    
    # 2. Second Ingestion (same data, different score)
    activities_updated = [
        {
            'sid': sid,
            'course_id': 'CS101',
            'course_name': 'Introduction to Computer Science',
            'test_type': 'Final',
            'score': 95,
            'academic_year': 2023,
            'semester': 1,
            'week': 16,
        }
    ]
    await repo.ingest_activities(activities_updated)
    await session.commit()
    session.expire_all()
    
    # Verify count remains 1 and score is updated
    res = await session.execute(select(Activity))
    all_activities = res.all()
    assert len(all_activities) == 1
    assert all_activities[0][0].activity_id == first_id
    assert all_activities[0][0].score == 95

@pytest.mark.asyncio
async def test_get_student_term_metrics(session: AsyncSession):
    repo = SqlAlchemyActivityRepository(session)
    query_service = SqlAlchemyStudentQueryService(session)
    sid = uuid.uuid4()
    
    # Seed data for multiple terms
    # Term 1: 2023-1, Score 80
    # Term 2: 2023-2, Score 90 (Prev should be 80)
    # Term 3: 2024-1, Score 100 (Prev should be (80+90)/2 = 85)
    activities = [
        {'sid': sid, 'course_id': 'C1', 'course_name': 'Course 1', 'test_type': 'T1', 'score': 80, 'academic_year': 2023, 'semester': 1, 'week': 1},
        {'sid': sid, 'course_id': 'C2', 'course_name': 'Course 2', 'test_type': 'T1', 'score': 90, 'academic_year': 2023, 'semester': 2, 'week': 1},
        {'sid': sid, 'course_id': 'C3', 'course_name': 'Course 3', 'test_type': 'T1', 'score': 100, 'academic_year': 2024, 'semester': 1, 'week': 1},
    ]
    await repo.ingest_activities(activities)
    await session.commit()
    
    # Query metrics
    metrics = await query_service.get_student_term_metrics(sid)
    assert len(metrics.terms) == 3
    
    # Terms are ordered desc by default
    t3 = metrics.terms[0] # 2024-1
    assert t3.academic_year == 2024
    assert t3.semester == 1
    assert t3.term_avg_score == 100.0
    assert t3.previous_terms_avg_score == 85.0
    assert len(t3.courses) == 1
    assert t3.courses[0].course_id == 'C3'
    
    t2 = metrics.terms[1] # 2023-2
    assert t2.academic_year == 2023
    assert t2.semester == 2
    assert t2.term_avg_score == 90.0
    assert t2.previous_terms_avg_score == 80.0
    
    t1 = metrics.terms[2] # 2023-1
    assert t1.academic_year == 2023
    assert t1.semester == 1
    assert t1.term_avg_score == 80.0
    assert t1.previous_terms_avg_score is None
