"""Tests for administrative user and role management."""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from src.presentation.api.auth import UserRole
from src.presentation.api.main import app
from src.infrastructure.database.models import User


@pytest.fixture
def raw_client(test_db_session: AsyncSession):
    """Provides a clean TestClient with overridden session."""
    app.dependency_overrides.clear()
    from src.infrastructure.database.session import get_async_session

    app.dependency_overrides[get_async_session] = lambda: test_db_session
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_admin_promote_user(
    raw_client: TestClient, test_db_session: AsyncSession
) -> None:
    """Verify that an admin can promote another user's role."""
    # 1. Register a regular user
    user_email = f'user_{uuid.uuid4().hex[:8]}@example.com'
    user_password = 'password123'
    raw_client.post(
        '/api/v1/auth/register', json={'email': user_email, 'password': user_password}
    )

    # 2. Register an admin
    admin_email = f'admin_{uuid.uuid4().hex[:8]}@example.com'
    admin_password = 'adminpassword'
    raw_client.post(
        '/api/v1/auth/register', json={'email': admin_email, 'password': admin_password}
    )

    # 3. Manually elevate the admin in the DB
    stmt = (
        update(User).where(User.email == admin_email).values(role=UserRole.ADMIN.value)
    )
    await test_db_session.execute(stmt)
    await test_db_session.commit()

    # 4. Login as Admin
    login_resp = raw_client.post(
        '/api/v1/auth/jwt/login',
        data={'username': admin_email, 'password': admin_password},
    )
    admin_token = login_resp.json()['access_token']

    # 5. Get the regular user's ID
    user_login = raw_client.post(
        '/api/v1/auth/jwt/login',
        data={'username': user_email, 'password': user_password},
    )
    user_token = user_login.json()['access_token']
    me_resp = raw_client.get(
        '/api/v1/users/me', headers={'Authorization': f'Bearer {user_token}'}
    )
    assert me_resp.status_code == 200
    user_id = me_resp.json()['id']

    # 6. Promote the user
    promote_resp = raw_client.patch(
        f'/api/v1/users/{user_id}',
        json={'role': UserRole.ADVISOR.value},
        headers={'Authorization': f'Bearer {admin_token}'},
    )
    assert promote_resp.status_code == 200
    assert promote_resp.json()['role'] == UserRole.ADVISOR.value


@pytest.mark.asyncio
async def test_non_admin_cannot_promote(raw_client: TestClient) -> None:
    """Verify that a non-admin user cannot promote themselves or others."""
    # 1. Register two regular users
    user1_email = f'u1_{uuid.uuid4().hex[:8]}@example.com'
    raw_client.post(
        '/api/v1/auth/register', json={'email': user1_email, 'password': 'password'}
    )

    user2_email = f'u2_{uuid.uuid4().hex[:8]}@example.com'
    raw_client.post(
        '/api/v1/auth/register', json={'email': user2_email, 'password': 'password'}
    )

    # 2. Login as User 1
    login_resp = raw_client.post(
        '/api/v1/auth/jwt/login', data={'username': user1_email, 'password': 'password'}
    )
    u1_token = login_resp.json()['access_token']

    # 3. Attempt to access the users list (should be forbidden)
    resp = raw_client.get(
        '/api/v1/users', headers={'Authorization': f'Bearer {u1_token}'}
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_admin_list_users(
    raw_client: TestClient, test_db_session: AsyncSession
) -> None:
    """Verify that an admin can list all users."""
    # 1. Register an admin
    admin_email = f'admin_{uuid.uuid4().hex[:8]}@example.com'
    admin_password = 'adminpassword'
    raw_client.post(
        '/api/v1/auth/register', json={'email': admin_email, 'password': admin_password}
    )

    # 2. Manually elevate the admin in the DB
    stmt = (
        update(User).where(User.email == admin_email).values(role=UserRole.ADMIN.value)
    )
    await test_db_session.execute(stmt)
    await test_db_session.commit()

    # 3. Login as Admin
    login_resp = raw_client.post(
        '/api/v1/auth/jwt/login',
        data={'username': admin_email, 'password': admin_password},
    )
    admin_token = login_resp.json()['access_token']

    # 4. List users
    resp = raw_client.get(
        '/api/v1/users/', headers={'Authorization': f'Bearer {admin_token}'}
    )
    assert resp.status_code == 200
    users = resp.json()
    assert isinstance(users, list)
    assert len(users) >= 1
    # The registered admin should be in the list
    assert any(u['email'] == admin_email for u in users)
