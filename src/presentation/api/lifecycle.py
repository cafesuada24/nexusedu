"""Lifecycle management for the FastAPI application.

This module handles the startup and shutdown procedures, initializes global
state, and manages the application lifespan.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any

from arq import ArqRedis, create_pool
from arq.connections import RedisSettings
from fastapi import FastAPI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.graph.state import CompiledStateGraph
from psycopg_pool import ConnectionPool

from src.core.config import config
from src.infrastructure.agents.agent import create_graph
from src.infrastructure.agents.state import AgentState
from src.core.logger import logger


@dataclass
class AppState:
    """State object held in the FastAPI app.state."""

    agent: CompiledStateGraph[AgentState, Any, AgentState]
    pool: ConnectionPool | None = None
    arq_pool: ArqRedis | None = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manages the startup and shutdown lifecycle of the FastAPI application."""
    # ==== Database ====
    # Schema is managed by Alembic migrations. Run: alembic upgrade head
    logger.info('API Lifecycle: Starting up (DB managed by Alembic)...')

    # ==== Agent Checkpointer ====
    postgres_uri = config.pg_dsn
    pool = None
    if postgres_uri:
        pool = ConnectionPool(conninfo=str(postgres_uri), max_size=20)
        checkpointer = PostgresSaver(pool)
        checkpointer.setup()
    else:
        checkpointer = MemorySaver()

    # ==== Agent ====
    agent = create_graph(checkpointer=checkpointer)

    # ==== ARQ Redis Pool ====
    try:
        arq_pool = await create_pool(
            RedisSettings(
                host=config.redis_host,
                port=config.redis_port,
            ),
        )
        logger.info('API Lifecycle: ARQ Redis Pool initialized.')
    except Exception as e:
        logger.warning(
            f'API Lifecycle: Could not connect to Redis: {e}. Background tasks will be disabled.'
        )
        arq_pool = None

    app.state.app_state = AppState(
        agent=agent,
        pool=pool,
        arq_pool=arq_pool,
    )

    yield

    if arq_pool:
        await arq_pool.close()
    if pool:
        pool.close()
