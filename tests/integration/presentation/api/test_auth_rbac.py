"""Integration tests for Auth and Role-Based Access Control."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import update

from src.infrastructure.database.models import User
from src.infrastructure.database.session import get_async_session
from src.presentation.api.auth import UserRole
from src.presentation.api.main import app

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
def raw_client(test_db_session: AsyncSession) -> TestClient:
    """Provides a TestClient without the current_active_user override."""
    # Ensure any residual overrides are cleared
    app.dependency_overrides.clear()

    app.dependency_overrides[get_async_session] = lambda: test_db_session

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


def test_auth_unauthorized(raw_client: TestClient) -> None:
    """Verify missing token returns 401 Unauthorized."""
    response = raw_client.get('/api/v1/alerts')
    assert response.status_code == 401


def test_auth_login_and_token(raw_client: TestClient) -> None:
    """Verify user registration and token issuance."""
    # 1. Register User
    email = f'test_login_{uuid.uuid4().hex[:8]}@example.com'
    password = 'securepassword'
    # Registration ignores role, so we register normally
    reg_response = raw_client.post(
        '/api/v1/api/v1/auth/register',  # Note the prefix in main.py is /api/v1 and auth router also has /auth
        json={'email': email, 'password': password},
    )
    # Wait, in main.py: api_v1_router.include_router(fastapi_users.get_register_router..., prefix="/auth")
    # And app.include_router(api_v1_router)
    # So it should be /api/v1/auth/register
    if reg_response.status_code == 404:
        reg_response = raw_client.post(
            '/api/v1/auth/register',
            json={'email': email, 'password': password},
        )

    assert reg_response.status_code == 201

    # 2. Login
    login_response = raw_client.post(
        '/api/v1/auth/jwt/login',
        data={'username': email, 'password': password},
    )
    assert login_response.status_code == 204
    # Check for cookie
    assert 'nexusedu_auth_token' in login_response.cookies


def test_auth_rbac_forbidden(raw_client: TestClient) -> None:
    """Verify viewer gets 403 when hitting admin endpoints."""
    # 1. Register & Login as Viewer (default)
    email = f'viewer_user_{uuid.uuid4().hex[:8]}@example.com'
    raw_client.post(
        '/api/v1/auth/register',
        json={'email': email, 'password': 'password'},
    )
    login_response = raw_client.post(
        '/api/v1/auth/jwt/login',
        data={'username': email, 'password': 'password'},
    )
    token = login_response.json()['access_token']

    # 2. Hit Admin Endpoint
    response = raw_client.post(
        '/api/v1/data/ingest',
        json={
            'batch_id': '123',
            'upload_timestamp': '2024-01-01T00:00:00',
            'data_sources': [],
        },
        headers={'Authorization': f'Bearer {token}'},
    )
    assert response.status_code == 403
    assert 'Insufficient permissions' in response.json()['detail']


@pytest.mark.asyncio
async def test_auth_rbac_advisor_vs_viewer(
    raw_client: TestClient, test_db_session: AsyncSession,
) -> None:
    """Verify advisor can write but viewer cannot."""
    # 1. Register a viewer and an advisor
    viewer_email = f'viewer_{uuid.uuid4().hex[:8]}@example.com'
    raw_client.post(
        '/api/v1/auth/register', json={'email': viewer_email, 'password': 'password'},
    )

    advisor_email = f'advisor_{uuid.uuid4().hex[:8]}@example.com'
    raw_client.post(
        '/api/v1/auth/register', json={'email': advisor_email, 'password': 'password'},
    )

    # Elevate to advisor
    stmt = (
        update(User)
        .where(User.email == advisor_email)
        .values(role=UserRole.ADVISOR.value)
    )
    await test_db_session.execute(stmt)
    await test_db_session.commit()

    # 2. Login as Viewer and try to patch alert (should fail)
    raw_client.post(
        '/api/v1/auth/jwt/login',
        data={'username': viewer_email, 'password': 'password'},
    )
    # Use case-centric route
    v_resp = raw_client.patch(
        f'/api/v1/cases/{uuid.uuid4()}/status',
        json={'status': 'sent'},
    )
    assert v_resp.status_code == 403

    # 3. Login as Advisor and try to patch alert (should pass authentication check)
    raw_client.post(
        '/api/v1/auth/jwt/login',
        data={'username': advisor_email, 'password': 'password'},
    )
    a_resp = raw_client.patch(
        f'/api/v1/cases/{uuid.uuid4()}/status',
        json={'status': 'sent'},
    )
    # Might be 404 because case doesn't exist, but NOT 403
    assert a_resp.status_code != 403


@pytest.mark.asyncio
async def test_auth_rbac_success(
    raw_client: TestClient, test_db_session: AsyncSession,
) -> None:
    """Verify admin can access admin endpoints."""
    # 1. Register
    email = f'admin_user_{uuid.uuid4().hex[:8]}@example.com'
    password = 'password'
    raw_client.post(
        '/api/v1/auth/register',
        json={'email': email, 'password': password},
    )

    # 2. Manually elevate to admin in the DB
    stmt = update(User).where(User.email == email).values(role=UserRole.ADMIN.value)
    await test_db_session.execute(stmt)
    await test_db_session.commit()

    # 3. Login
    raw_client.post(
        '/api/v1/auth/jwt/login',
        data={'username': email, 'password': password},
    )

    # 4. Hit Admin Endpoint
    response = raw_client.post(
        '/api/v1/data/ingest',
        json={
            'batch_id': '123',
            'upload_timestamp': '2024-01-01T00:00:00',
            'data_sources': [],
        },
    )
    # Should not be 401 or 403
    assert response.status_code != 401
    assert response.status_code != 403
