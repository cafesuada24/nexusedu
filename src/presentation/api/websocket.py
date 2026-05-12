"""WebSocket connection management.

This module provides a manager to track active WebSocket connections and
facilitate message broadcasting to specific users or all connected clients.
"""

import uuid
from typing import Any

import structlog
from fastapi import WebSocket

logger = structlog.get_logger(__name__)


class WebSocketManager:
    """Manages active WebSocket connections."""

    def __init__(self) -> None:
        """Initialize the connection manager."""
        # Map user_id to a list of active WebSockets (to support multiple tabs)
        self.active_connections: dict[uuid.UUID, list[WebSocket]] = {}

    async def connect(self, user_id: uuid.UUID, websocket: WebSocket) -> None:
        """Accepts a connection and stores it in the active connections map."""
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        logger.debug(
            'WS: User connected',
            user_id=str(user_id),
            total_users=len(self.active_connections),
        )

    def disconnect(self, user_id: uuid.UUID, websocket: WebSocket) -> None:
        """Removes a connection from the active connections map."""
        if user_id in self.active_connections:
            self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        logger.debug(
            'WS: User disconnected',
            user_id=str(user_id),
            total_users=len(self.active_connections),
        )

    async def send_personal_message(self, message: dict[str, Any], user_id: uuid.UUID) -> None:
        """Sends a message to all active connections for a specific user."""
        if user_id in self.active_connections:
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(
                        'WS: Failed to send personal message',
                        user_id=str(user_id),
                        error=str(e),
                    )

    async def broadcast(self, message: dict[str, Any]) -> None:
        """Sends a message to all active connections across all users."""
        for user_id, connections in self.active_connections.items():
            for connection in connections:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(
                        'WS: Failed to broadcast message',
                        user_id=str(user_id),
                        error=str(e),
                    )


# Global instance
ws_manager = WebSocketManager()
