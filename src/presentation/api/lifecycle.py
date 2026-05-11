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

from src.core.config import config
from src.core.logger import logger
from src.infrastructure.extern.presidio_pii_masker import PresidioPiiMasker


@dataclass
class AppState:
    """State object held in the FastAPI app.state."""

    arq_pool: ArqRedis | None = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manages the startup and shutdown lifecycle of the FastAPI application."""
    # ==== Database ====
    # Schema is managed by Alembic migrations. Run: alembic upgrade head
    logger.info('API Lifecycle: Starting up (DB managed by Alembic)...')

    # ==== PII Masker Warmup ====
    # Pre-load heavy NLP models once during startup
    logger.info('API Lifecycle: Warming up PII Masker...')
    PresidioPiiMasker()

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
            f'API Lifecycle: Could not connect to Redis: {e}. Background tasks will be disabled.',
        )
        arq_pool = None

    app.state.app_state = AppState(
        arq_pool=arq_pool,
    )

    yield

    if arq_pool:
        await arq_pool.close()
