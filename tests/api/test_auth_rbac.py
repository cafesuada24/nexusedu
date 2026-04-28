"""Integration tests for Auth and Role-Based Access Control."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING
import asyncio

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import update

from src.api.auth import async_session_maker, User, UserRole
from src.api.lifecycle import get_agent, get_dbmanager
from src.api.main import app

if TYPE_CHECKING:
    from src.database.manager import DatabaseManager


@pytest.fixture
def raw_client(test_db_manager: DatabaseManager, mock_agent) -> TestClient:
    """Provides a TestClient without the current_active_user override."""
    # Ensure any residual overrides are cleared
    app.dependency_overrides.clear()

    app.dependency_overrides[get_agent] = lambda: mock_agent
    app.dependency_overrides[get_dbmanager] = lambda: test_db_manager

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


def test_auth_unauthorized(raw_client: TestClient) -> None:
    """Verify missing token returns 401 Unauthorized."""
    response = raw_client.get('/api/v1/alerts/')
    assert response.status_code == 401


def test_auth_login_and_token(raw_client: TestClient) -> None:
    """Verify user registration and token issuance."""
    # 1. Register User
    email = f'test_login_{uuid.uuid4().hex[:8]}@example.com'
    password = 'securepassword'
    # Registration ignores role, so we register normally
    reg_response = raw_client.post(
        '/api/v1/auth/register',
        json={'email': email, 'password': password},
    )
    assert reg_response.status_code == 201

    # 2. Login
    login_response = raw_client.post(
        '/api/v1/auth/jwt/login', data={'username': email, 'password': password}
    )
    assert login_response.status_code == 200
    data = login_response.json()
    assert 'access_token' in data
    assert data['token_type'] == 'bearer'


def test_auth_rbac_forbidden(raw_client: TestClient) -> None:
    """Verify viewer gets 403 when hitting admin endpoints."""
    # 1. Register & Login as Viewer (default)
    email = f'viewer_user_{uuid.uuid4().hex[:8]}@example.com'
    raw_client.post(
        '/api/v1/auth/register',
        json={'email': email, 'password': 'password'},
    )
    login_response = raw_client.post(
        '/api/v1/auth/jwt/login', data={'username': email, 'password': 'password'}
    )
    token = login_response.json()['access_token']

    # 2. Hit Admin Endpoint
    response = raw_client.post(
        '/api/v1/data/ingest',
        json={'batch_id': '123', 'data_sources': []},
        headers={'Authorization': f'Bearer {token}'},
    )
    assert response.status_code == 403
    assert 'Insufficient permissions' in response.json()['detail']


def test_auth_rbac_advisor_vs_viewer(raw_client: TestClient) -> None:
    """Verify advisor can write but viewer cannot."""
    # 1. Register a viewer and an advisor
    viewer_email = f'viewer_{uuid.uuid4().hex[:8]}@example.com'
    raw_client.post('/api/v1/auth/register', json={'email': viewer_email, 'password': 'password'})

    advisor_email = f'advisor_{uuid.uuid4().hex[:8]}@example.com'
    raw_client.post('/api/v1/auth/register', json={'email': advisor_email, 'password': 'password'})

    async def elevate_to_advisor():
        async with async_session_maker() as session:
            stmt = update(User).where(User.email == advisor_email).values(role=UserRole.ADVISOR.value)
            await session.execute(stmt)
            await session.commit()
    asyncio.run(elevate_to_advisor())

    # 2. Login as Viewer and try to patch alert (should fail)
    v_login = raw_client.post('/api/v1/auth/jwt/login', data={'username': viewer_email, 'password': 'password'})
    v_token = v_login.json()['access_token']
    v_resp = raw_client.patch(
        '/api/v1/alerts/S123/status',
        json={'status': 'sent'},
        headers={'Authorization': f'Bearer {v_token}'}
    )
    assert v_resp.status_code == 403

    # 3. Login as Advisor and try to patch alert (should pass authentication check)
    a_login = raw_client.post('/api/v1/auth/jwt/login', data={'username': advisor_email, 'password': 'password'})
    a_token = a_login.json()['access_token']
    a_resp = raw_client.patch(
        '/api/v1/alerts/S123/status',
        json={'status': 'sent'},
        headers={'Authorization': f'Bearer {a_token}'}
    )
    # Might be 404 or 500 because student S123 doesn't exist, but NOT 403
    assert a_resp.status_code != 403


def test_auth_rbac_success(raw_client: TestClient) -> None:
    """Verify admin:all can access admin endpoints."""
    # 1. Register
    email = f'admin_user_{uuid.uuid4().hex[:8]}@example.com'
    password = 'password'
    raw_client.post(
        '/api/v1/auth/register',
        json={'email': email, 'password': password},
    )

    # 2. Manually elevate to admin in the DB (since registration ignores role)
    async def elevate_user():
        async with async_session_maker() as session:
            stmt = update(User).where(User.email == email).values(role=UserRole.ADMIN.value)
            await session.execute(stmt)
            await session.commit()

    asyncio.run(elevate_user())

    # 3. Login
    login_response = raw_client.post(
        '/api/v1/auth/jwt/login', data={'username': email, 'password': password}
    )
    token = login_response.json()['access_token']

    # 4. Hit Admin Endpoint
    response = raw_client.post(
        '/api/v1/data/ingest',
        json={'batch_id': '123', 'data_sources': []},
        headers={'Authorization': f'Bearer {token}'},
    )
    # The endpoint might return 400 or something if data is bad, but shouldn't return 401 or 403
    assert response.status_code != 401
    assert response.status_code != 403
