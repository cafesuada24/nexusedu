"""Monitoring and health check routes for the API."""

from datetime import UTC, datetime
from typing import Annotated, Any

from arq import ArqRedis
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.session import get_async_session
from src.presentation.dependencies.providers import get_arq_pool

router = APIRouter(tags=['monitoring'])


@router.get('/health')
async def health_check(
    arq_pool: Annotated[ArqRedis | None, Depends(get_arq_pool)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> dict[str, Any]:
    """Provides the operational status of the API and its core dependencies.

    Returns:
        A dictionary containing the status of various system components.
    """
    # 1. Check AI Connectivity (Cached result from background worker)
    if arq_pool:
        cached_status = await arq_pool.get('ai_health_status')
        if cached_status:
            # arq returns bytes, so we decode it
            ai_status = cached_status.decode('utf-8') if isinstance(cached_status, bytes) else str(cached_status)
        else:
            ai_status = 'unhealthy: pending first background check'
    else:
        ai_status = 'unhealthy: cache pool not initialized'

    # 2. Check Database Connectivity
    try:
        await session.execute(text('SELECT 1'))
        db_status = 'healthy'
    except Exception as e:
        db_status = f'unhealthy: {str(e)}'

    # 3. Check ARQ/Redis Connectivity
    if arq_pool:
        try:
            await arq_pool.ping()
            arq_status = 'healthy'
        except Exception as e:
            arq_status = f'unhealthy: {str(e)}'
    else:
        arq_status = 'unhealthy: pool not initialized'

    all_healthy = all(s == 'healthy' for s in [ai_status, db_status, arq_status])

    return {
        'status': 'operational' if all_healthy else 'degraded',
        'timestamp': datetime.now(UTC).isoformat(),
        'dependencies': {
            'ai_engine': ai_status,
            'database': db_status,
            'background_worker': arq_status,
        },
        'version': '1.0.0',
    }
