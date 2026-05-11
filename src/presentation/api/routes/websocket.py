"""WebSocket routes for real-time updates."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect

from src.core.logger import logger
from src.presentation.api.auth import UserManager, get_jwt_strategy, get_user_manager
from src.presentation.api.websocket import ws_manager

router = APIRouter(tags=['websocket'])


@router.websocket('/ws')
async def websocket_endpoint(
    websocket: WebSocket,
    token: Annotated[str, Query(...)],
    user_manager: Annotated[UserManager, Depends(get_user_manager)],
) -> None:
    """Entry point for real-time WebSocket communication."""
    # Authenticate using JWT strategy
    strategy = get_jwt_strategy()
    user = await strategy.read_token(token, user_manager)

    if not user or not user.is_active:
        logger.warning('WS: Connection rejected - invalid or inactive user.')
        # WebSocket.close() should be called after accept() if we want to send a code,
        # or we can just not accept. But let's accept and then close if unauthorized
        # to ensure the client gets the message.
        await websocket.accept()
        await websocket.close(code=4003)  # Forbidden
        return

    await ws_manager.connect(user.id, websocket)
    try:
        while True:
            # Keep connection alive; handle incoming messages if needed
            # Using receive_text() as a heartbeat/keep-alive mechanism
            data = await websocket.receive_text()
            logger.info(f"Received: {data}")
    except WebSocketDisconnect:
        logger.info(f"WS disconnected normally: {user.id}")
    except Exception as e:
        logger.error(f'WS: Unexpected error for user {user.id}: {e}')
    finally:
        ws_manager.disconnect(user.id, websocket)
