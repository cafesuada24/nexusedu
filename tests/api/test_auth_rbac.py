"""Integration tests for Auth and Role-Based Access Control."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

import pytest
from fastapi.testclient import TestClient

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
    reg_response = raw_client.post(
        '/api/v1/auth/register',
        json={'email': email, 'password': password, 'role': 'advisor:read'},
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
    """Verify advisor:read gets 403 when hitting admin:all endpoints."""
    # 1. Register & Login as Advisor
    email = f'advisor_read_{uuid.uuid4().hex[:8]}@example.com'
    raw_client.post(
        '/api/v1/auth/register',
        json={'email': email, 'password': 'password', 'role': 'advisor:read'},
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
    assert 'Forbidden' in response.json()['detail']


def test_auth_rbac_success(raw_client: TestClient) -> None:
    """Verify admin:all can access admin endpoints."""
    # 1. Register & Login as Admin
    email = f'admin_user_{uuid.uuid4().hex[:8]}@example.com'
    raw_client.post(
        '/api/v1/auth/register',
        json={'email': email, 'password': 'password', 'role': 'admin:all'},
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
    # The endpoint might return 400 or something if data is bad, but shouldn't return 401 or 403
    assert response.status_code != 401
    assert response.status_code != 403
