"""WebSocket routes for real-time updates."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, status
from fastapi_users import BaseUserManager

from src.core.logger import logger
from src.infrastructure.database.models import User
from src.presentation.api.auth import (
    get_jwt_strategy,
    get_user_manager,
)
from src.presentation.api.websocket import ws_manager

router = APIRouter(tags=['websocket'])


async def get_ws_current_user(
    websocket: WebSocket,
    user_manager: Annotated[
        BaseUserManager[User, UUID],
        Depends(get_user_manager),
    ],
) -> User:
    strategy = get_jwt_strategy()

    token = websocket.cookies.get('nexusedu_auth_token')

    if not token:
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION,
        )

        raise WebSocketDisconnect(
            code=status.WS_1008_POLICY_VIOLATION,
        )


    user = await strategy.read_token(
        token,
        user_manager,
    )

    if not user or not user.is_active:
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION,
        )

        raise WebSocketDisconnect(
            code=status.WS_1008_POLICY_VIOLATION,
        )

    return user


@router.websocket('/ws')
async def websocket_endpoint(
    websocket: WebSocket,
    user: Annotated[User, Depends(get_ws_current_user)],
) -> None:
    """Entry point for real-time WebSocket communication."""
    await ws_manager.connect(
        user.id,
        websocket,
    )

    try:
        while True:
            await websocket.receive()

    except WebSocketDisconnect:
        logger.info(
            f'WS disconnected: {user.id}',
        )

    except Exception:
        logger.error(
            f'Unexpected WS error: {user.id}',
        )

    finally:
        ws_manager.disconnect(
            user.id,
            websocket,
        )
