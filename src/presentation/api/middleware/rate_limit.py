"""Rate limiting middleware using Redis or in-memory fallback."""

import time
from collections.abc import Awaitable, Callable

import structlog
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse

logger = structlog.get_logger(__name__)

# Note: For multi-worker production, always use Redis.
# This implementation remains in-memory for this refactor phase
# but is moved to a dedicated module for better separation of concerns.

rate_limit_store: dict[str, list[float]] = {}
RATE_LIMIT_CALLS = 100
RATE_LIMIT_WINDOW = 60  # seconds


async def rate_limit_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Simple rate limiting middleware based on client host."""
    client_ip = request.client.host if request.client else 'unknown'
    now = time.time()

    # Clean up old timestamps
    if client_ip in rate_limit_store:
        rate_limit_store[client_ip] = [
            ts for ts in rate_limit_store[client_ip] if now - ts < RATE_LIMIT_WINDOW
        ]
    else:
        rate_limit_store[client_ip] = []

    if len(rate_limit_store[client_ip]) >= RATE_LIMIT_CALLS:
        logger.warning('Rate limit exceeded', client_ip=client_ip)
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={'detail': 'Too many requests. Please try again later.'},
        )

    rate_limit_store[client_ip].append(now)
    return await call_next(request)
