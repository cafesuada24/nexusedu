"""WebSocket routes for real-time updates."""

from typing import Annotated
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, status
from fastapi_users import BaseUserManager

from src.infrastructure.database.models import User
from src.presentation.api.auth import (
    get_jwt_strategy,
    get_user_manager,
)
from src.presentation.api.websocket import ws_manager

logger = structlog.get_logger(__name__)


router = APIRouter(tags=['websocket'])


async def get_ws_current_user(
    websocket: WebSocket,
    user_manager: Annotated[
        BaseUserManager[User, UUID],
        Depends(get_user_manager),
    ],
) -> User | None:
    """Dependency to authenticate WebSocket connections via cookies or query params."""
    strategy = get_jwt_strategy()

    # Try cookie first
    token = websocket.cookies.get('nexusedu_auth_token')

    # Fallback to query parameter for cross-origin connections
    if not token:
        token = websocket.query_params.get('token')

    if not token:
        logger.warning('WebSocket connection attempt without token')
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION,
        )
        return None

    user = await strategy.read_token(
        token,
        user_manager,
    )

    if not user or not user.is_active:
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION,
        )
        return None

    return user


@router.websocket('/ws')
async def websocket_endpoint(
    websocket: WebSocket,
    user: Annotated[User | None, Depends(get_ws_current_user)],
) -> None:
    """Entry point for real-time WebSocket communication."""
    if user is None:
        return

    try:
        await ws_manager.connect(
            user.id,
            websocket,
        )

        while True:
            await websocket.receive()

    except WebSocketDisconnect:
        logger.info(
            'WS disconnected',
            user_id=str(user.id),
        )

    except Exception:
        logger.error(
            'Unexpected WS error',
            user_id=str(user.id),
        )

    finally:
        ws_manager.disconnect(
            user.id,
            websocket,
        )
