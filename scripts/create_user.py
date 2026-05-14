"""CLI script to create a user account with a specific role."""

import argparse
import asyncio
import logging

from dotenv import load_dotenv
from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase

from src.infrastructure.database.models import User
from src.infrastructure.database.session import async_session_maker
from src.infrastructure.persistence.repositories.sqlalchemy_repositories import (
    SqlAlchemyUserSettingsRepository,
)
from src.infrastructure.persistence.sqlalchemy_uow import SqlAlchemyUnitOfWork
from src.presentation.api.auth import (
    UserManager,
    UserRole,
)
from src.presentation.schemas.auth import UserCreate, UserUpdate  # noqa: E402

load_dotenv()


async def create_user(email: str, password: str, role: str) -> None:
    """Create a user and optionally update their role."""
    async with async_session_maker() as session:
        user_db = SQLAlchemyUserDatabase(session, User)
        settings_repo = SqlAlchemyUserSettingsRepository(session)
        uow = SqlAlchemyUnitOfWork(session)

        user_manager = UserManager(user_db, settings_repo, uow)

        # 1. Create user
        user_create = UserCreate(email=email, password=password)
        try:
            user = await user_manager.create(user_create)
            logging.info(f'User created successfully: {user.email} (ID: {user.id})')

            # 2. Update role if not viewer
            if role != UserRole.VIEWER.value:
                try:
                    user_role = UserRole(role)
                    user_update = UserUpdate(role=user_role)
                    # Use user_manager.update to trigger on_after_update (advisor linkage)
                    await user_manager.update(user_update, user)
                    await session.commit()
                    logging.info(f'User role updated to: {user_role.value}')
                except ValueError:
                    logging.error(f"Error: Invalid role '{role}'. Defaulting to 'viewer'.")
                    logging.error(f'Available roles: {[r.value for r in UserRole]}')
            else:
                await session.commit()
                print('User role set to: viewer')

        except Exception as e:
            logging.error(f'Error creating user: {e}', exc_info=True)
            await session.rollback()


def main() -> None:
    parser = argparse.ArgumentParser(description='Create a user account.')
    parser.add_argument('--email', required=True, help='User email')
    parser.add_argument('--password', required=True, help='User password')
    parser.add_argument(
        '--role',
        default='viewer',
        choices=[r.value for r in UserRole],
        help='User role (default: viewer)',
    )

    args = parser.parse_args()

    asyncio.run(create_user(args.email, args.password, args.role))


if __name__ == '__main__':
    main()
