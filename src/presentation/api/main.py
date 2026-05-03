"""Main entry point for the Agent Assistant API.

This module initializes the FastAPI application, configures middleware,
and includes the API routers for the agent's functionality.
"""

import time
from collections.abc import Awaitable, Callable

from fastapi import APIRouter, FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.core.config import config
from src.core.logger import logger
from src.presentation.api.auth import auth_backend, fastapi_users
from src.presentation.api.lifecycle import lifespan
from src.presentation.api.middleware.rate_limit import rate_limit_middleware
from src.presentation.api.routes import (
    advisors,
    alerts,
    data,
    health,
    jobs,
    metrics,
    query,
    users,
)
from src.presentation.schemas.auth import UserCreate, UserRead

app = FastAPI(
    title='Agent Assistant API',
    description='API to interact with the LangGraph Agent for data analysis and visualization.',
    version='1.0.0',
    lifespan=lifespan,
)

# CORS Configuration
allowed_origins_str = config.allowed_origins
allowed_origins = [
    origin.strip() for origin in allowed_origins_str.split(',') if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

# Rate Limiting Middleware
app.middleware('http')(rate_limit_middleware)


# Logging Middleware
@app.middleware('http')
async def log_requests(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Logs the details of incoming HTTP requests and their processing time."""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    logger.info(
        f'HTTP: {request.method} {request.url.path} - Status: {response.status_code} - Duration: {process_time:.2f}s',
    )
    return response


@app.exception_handler(Exception)
async def global_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
    """Catches all unhandled exceptions and returns a sanitized JSON response."""
    logger.error(f'Unhandled Exception: {exc}', exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            'detail': 'An unexpected internal error occurred.',
            'type': type(exc).__name__,
        },
    )


@app.exception_handler(ValueError)
async def value_error_handler(_request: Request, exc: ValueError) -> JSONResponse:
    """Handles validation errors specifically."""
    logger.warning(f'Validation Error: {exc}')
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            'detail': str(exc),
            'type': 'ValidationError',
        },
    )


try:
    from sqlglot import ParseError as SQLParseError
except ImportError:
    SQLParseError = Exception


@app.exception_handler(SQLParseError)
async def sql_parse_error_handler(_request: Request, exc: Exception) -> JSONResponse:
    """Handles SQL parsing errors specifically."""
    logger.warning(f'SQL Parse Error: {exc}')
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            'detail': 'The generated or provided SQL query is invalid.',
            'type': 'SQLParseError',
        },
    )


# API v1 Router
api_v1_router = APIRouter(prefix='/api/v1')

# Include Auth routes
api_v1_router.include_router(
    fastapi_users.get_auth_router(auth_backend),
    prefix='/auth/jwt',
    tags=['auth'],
)
api_v1_router.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix='/auth',
    tags=['auth'],
)

# User Management
api_v1_router.include_router(users.router)


@api_v1_router.get('/')
async def root() -> dict[str, str]:
    """Provides a welcome message and documentation link."""
    return {
        'message': 'Welcome to the Agent Assistant API v1. Access /docs for Swagger documentation.',
        'docs': '/docs',
    }


# Include routers
api_v1_router.include_router(health.router)
api_v1_router.include_router(jobs.router)
api_v1_router.include_router(query.router)
api_v1_router.include_router(data.router)
api_v1_router.include_router(alerts.router)
api_v1_router.include_router(advisors.router)
api_v1_router.include_router(metrics.router)

app.include_router(api_v1_router)

if __name__ == '__main__':
    import uvicorn

    uvicorn.run(app, host='0.0.0.0', port=8000)
