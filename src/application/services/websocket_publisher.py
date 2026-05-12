"""Service for publishing events to the WebSocket Pub/Sub channel."""

import json
import uuid
from typing import Any

import structlog
from arq import ArqRedis

logger = structlog.get_logger(__name__)


class WebSocketEventPublisher:
    """Publishes messages to Redis for WebSocket broadcasting."""

    def __init__(self, redis_pool: ArqRedis) -> None:
        """Initialize with a Redis connection pool."""
        self.redis_pool = redis_pool

    async def publish(
        self,
        event_type: str,
        payload: dict[str, Any],
        user_id: uuid.UUID | None = None,
    ) -> None:
        """Publishes a message to the ws_updates channel."""
        message = {
            'type': event_type,
            'payload': payload,
            'user_id': str(user_id) if user_id else None,
        }
        try:
            await self.redis_pool.publish('ws_updates', json.dumps(message))
            logger.debug(
                'WS message published to Redis',
                event_type=event_type,
            )
        except Exception as e:
            logger.error(
                'Failed to publish WS message to Redis',
                event_type=event_type,
                error=str(e),
            )
