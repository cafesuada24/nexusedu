"""Lifecycle management for the FastAPI application.

This module handles the startup and shutdown procedures, initializes global
state, and manages the application lifespan.
"""

import asyncio
import contextlib
import json
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from dataclasses import dataclass

import redis.asyncio as redis
import structlog
from arq import ArqRedis, create_pool
from arq.connections import RedisSettings
from fastapi import FastAPI

from src.core.config import config
from src.infrastructure.extern.presidio_pii_masker import PresidioPiiMasker
from src.presentation.api.websocket import ws_manager

logger = structlog.get_logger(__name__)


@dataclass
class AppState:
    """State object held in the FastAPI app.state."""

    arq_pool: ArqRedis | None = None


async def redis_pubsub_listener() -> None:
    """Listens to Redis Pub/Sub and broadcasts messages to WebSockets."""
    r = redis.Redis(
        host=config.redis_host,
        port=config.redis_port,
        decode_responses=True,
        password=config.redis_password,
    )
    pubsub = r.pubsub()

    try:
        await pubsub.subscribe('ws_updates')
        logger.info(
            'API Lifecycle: Redis Pub/Sub listener started on channel "ws_updates".'
        )
        async for message in pubsub.listen():
            if message['type'] == 'message':
                try:
                    data = json.loads(message['data'])
                    # msg_type = data.get('type')
                    # payload = data.get('payload', {})
                    user_id_str = data.get('user_id')

                    if user_id_str:
                        user_id = uuid.UUID(user_id_str)
                        await ws_manager.send_personal_message(data, user_id)
                    else:
                        await ws_manager.broadcast(data)
                except Exception as e:
                    logger.error(
                        'API Lifecycle: Error processing Pub/Sub message', error=str(e)
                    )
    except redis.ConnectionError:
        logger.info('API Lifecycle: Redis Pub/Sub listener stopping...')
    except asyncio.CancelledError:
        logger.info('API Lifecycle: Redis Pub/Sub listener stopping...')
        await pubsub.unsubscribe('ws_updates')
    finally:
        await r.close()


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

    # ==== Redis Pub/Sub Listener ====
    pubsub_task = asyncio.create_task(redis_pubsub_listener())

    # ==== ARQ Redis Pool ====
    try:
        arq_pool = await create_pool(
            RedisSettings(
                host=config.redis_host,
                port=config.redis_port,
                password=config.redis_password,
            ),
        )
        logger.info('API Lifecycle: ARQ Redis Pool initialized.')
    except Exception as e:
        logger.warning(
            'Could not connect to Redis. Background tasks will be disabled.',
            error=str(e),
        )
        arq_pool = None

    app.state.app_state = AppState(
        arq_pool=arq_pool,
    )

    yield

    # ==== Shutdown ====
    pubsub_task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await pubsub_task

    if arq_pool:
        await arq_pool.close()
