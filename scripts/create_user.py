"""CLI script to create a user account with a specific role."""

import argparse
import asyncio

from dotenv import load_dotenv

from src.application.services.event_publisher import TaskQueueEventPublisher
from src.infrastructure.database.models import User
from src.infrastructure.database.session import async_session_maker
from src.infrastructure.persistence.repositories.sqlalchemy_repositories import (
    SqlAlchemyAdvisorRepository,
    SqlAlchemyUserSettingsRepository,
)
from src.infrastructure.queue.outbox_adapter import TransactionalOutboxAdapter
from src.presentation.api.auth import (
    SQLAlchemyUserDatabase,
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
        advisor_repo = SqlAlchemyAdvisorRepository(session)

        # Instantiate EventPublisher via Outbox for transactional consistency
        outbox_queue = TransactionalOutboxAdapter(session)
        event_publisher = TaskQueueEventPublisher(outbox_queue)

        user_manager = UserManager(user_db, settings_repo, advisor_repo, event_publisher)

        # 1. Create user
        user_create = UserCreate(email=email, password=password)
        try:
            user = await user_manager.create(user_create)
            print(f'User created successfully: {user.email} (ID: {user.id})')

            # 2. Update role if not viewer
            if role != UserRole.VIEWER.value:
                try:
                    user_role = UserRole(role)
                    user_update = UserUpdate(role=user_role)
                    # Use user_manager.update to trigger on_after_update (advisor linkage)
                    await user_manager.update(user_update, user)
                    await session.commit()
                    print(f'User role updated to: {user_role.value}')
                except ValueError:
                    print(f"Error: Invalid role '{role}'. Defaulting to 'viewer'.")
                    print(f'Available roles: {[r.value for r in UserRole]}')
            else:
                await session.commit()
                print('User role set to: viewer')

        except Exception as e:
            print(f'Error creating user: {e}')
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
