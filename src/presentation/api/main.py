"""Main entry point for the Agent Assistant API.

This module initializes the FastAPI application, configures middleware,
and includes the API routers for the agent's functionality.
"""

import time
from collections.abc import Awaitable, Callable

import structlog
from fastapi import APIRouter, FastAPI, Request, Response, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.core.config import config
from src.core.otel import setup_otel
from src.domain import exceptions as domain_exc
from src.presentation.api.auth import auth_backend, fastapi_users
from src.presentation.api.lifecycle import lifespan
from src.presentation.api.middleware.rate_limit import rate_limit_middleware
from src.presentation.api.routes import (
    admin,
    advisors,
    cases,
    data,
    health,
    jobs,
    metrics,
    notifications,
    students,
    users,
    websocket,
)
from src.presentation.schemas.auth import UserCreate, UserRead

logger = structlog.get_logger(__name__)


app = FastAPI(
    title='Agent Assistant API',
    description='API for student intervention and performance tracking.',
    version='1.0.0',
    lifespan=lifespan,
)

# Initialize OpenTelemetry
setup_otel(app)

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
        'HTTP request processed',
        method=request.method,
        path=request.url.path,
        status=response.status_code,
        duration=process_time,
    )
    return response


@app.exception_handler(WebSocketDisconnect)
async def websocket_disconnect_handler(
    _request: Request,
    _exc: WebSocketDisconnect,
) -> None:
    """Handles WebSocketDisconnect exceptions.

    These are expected when a client disconnects and don't need to be logged as errors.
    """
    return


@app.exception_handler(domain_exc.DomainError)
async def domain_error_handler(
    _request: Request,
    exc: domain_exc.DomainError,
) -> JSONResponse:
    """Maps domain errors to appropriate HTTP status codes."""
    # Define mapping of exception types to status codes
    not_found_errors = (
        domain_exc.CaseNotFoundError,
        domain_exc.StudentNotFoundError,
        domain_exc.TaskNotFoundError,
        domain_exc.AdvisorNotFoundError,
        domain_exc.WorkingHoursNotFoundError,
        domain_exc.EmailNotFoundError,
        domain_exc.JobNotFoundError,
    )

    unauthorized_errors = (domain_exc.UnauthorizedError,)

    if isinstance(exc, not_found_errors):
        status_code = status.HTTP_404_NOT_FOUND
    elif isinstance(exc, unauthorized_errors):
        status_code = status.HTTP_403_FORBIDDEN
    else:
        # Default to 400 Bad Request for other domain/validation errors
        status_code = status.HTTP_400_BAD_REQUEST

    logger.warning(
        'Domain error occurred',
        error=str(exc),
        type=type(exc).__name__,
        status_code=status_code,
    )
    return JSONResponse(
        status_code=status_code,
        content={
            'detail': str(exc),
            'type': type(exc).__name__,
        },
    )


@app.exception_handler(domain_exc.InvalidActionError)
async def invalid_action_error_handler(
    _request: Request,
    exc: domain_exc.InvalidActionError,
) -> JSONResponse:
    """Specific handler for InvalidActionError (which doesn't inherit from DomainError)."""
    logger.warning('Invalid action error occurred', error=str(exc))
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            'detail': str(exc),
            'type': 'InvalidActionError',
        },
    )


@app.exception_handler(Exception)
async def global_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
    """Catches all unhandled exceptions and returns a sanitized JSON response."""
    logger.error('Unhandled exception occurred', error=str(exc), exc_info=True)
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
    logger.warning('Validation error occurred', error=str(exc))
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            'detail': str(exc),
            'type': 'ValidationError',
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
api_v1_router.include_router(data.router)
api_v1_router.include_router(cases.router)
api_v1_router.include_router(advisors.router)
api_v1_router.include_router(metrics.router)
api_v1_router.include_router(notifications.router)
api_v1_router.include_router(students.router)
api_v1_router.include_router(admin.router)
api_v1_router.include_router(websocket.router)

app.include_router(api_v1_router)

if __name__ == '__main__':
    import uvicorn

    uvicorn.run(app, host='0.0.0.0', port=8000)
