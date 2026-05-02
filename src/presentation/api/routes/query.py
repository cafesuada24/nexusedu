"""API routes for agent queries."""

import uuid
from typing import Annotated
from uuid import UUID

from arq import ArqRedis
from fastapi import APIRouter, Depends, Header, HTTPException, Query

from src.domain.repositories.idempotency_repository import IdempotencyRepository
from src.presentation.api.auth import Scope, User, require_scope
from src.presentation.dependencies.providers import (
    get_arq_pool,
    get_idempotency_repository,
)
from src.core.logger import logger

router = APIRouter(prefix='/query', tags=['query'])


@router.post('', status_code=202)
async def submit_query(
    query: str,
    arq_pool: Annotated[ArqRedis | None, Depends(get_arq_pool)],
    user: Annotated[User, Depends(require_scope(Scope.QUERY_EXECUTE))],
    idempotency_repo: Annotated[
        IdempotencyRepository, Depends(get_idempotency_repository)
    ],
    thread_id: str | None = Query(None, description='Existing thread identifier.'),
    idempotency_key: Annotated[str | None, Header(alias='Idempotency-Key')] = None,
) -> dict[str, str]:
    """Submits a natural language query for processing by the agent.

    The query is processed in the background via ARQ, and a job ID is returned to track status.
    """
    if idempotency_key:
        idemp_key = UUID(idempotency_key)
        if await idempotency_repo.check_key(idemp_key):
            logger.info(f'Idempotency hit for submit_query: {idemp_key}')
            return {'status': 'success', 'message': 'Query already submitted (idempotent).'}

    if not arq_pool:
        raise HTTPException(
            status_code=503, detail='Background processing unavailable (Redis down).'
        )

    job_id = str(uuid.uuid4())

    # User info for agent context
    user_dict = {
        'id': str(user.id),
        'role': user.role,
        'email': user.email,
    }

    # Enqueue ARQ job
    await arq_pool.enqueue_job(
        'run_agent_task',
        job_id=job_id,
        query=query,
        thread_id=thread_id,
        user_dict=user_dict,
    )

    if idempotency_key:
        await idempotency_repo.record_key(UUID(idempotency_key))

    return {'job_id': job_id}
