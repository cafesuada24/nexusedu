"""Database session management for unified SQLAlchemy access."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.utils.env import getenv

# Unified Database URL. Defaults to a local SQLite file using aiosqlite for async support.
DATABASE_URL: str = getenv('DATABASE_URL', 'sqlite+aiosqlite:///./data/app.db')

engine = create_async_engine(DATABASE_URL)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting an asynchronous SQLAlchemy session.

    Automatically handles the transaction lifecycle by committing on success
    and rolling back on exceptions.

    Yields:
        An async SQLAlchemy session.
    """
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
