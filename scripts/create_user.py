"""CLI script to create a user account with a specific role."""

import argparse
import asyncio
import uuid
import sys
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from sqlalchemy import update
from src.api.auth import (
    User,
    UserManager,
    UserRole,
    async_session_maker,
    SQLAlchemyUserDatabase,
)
from src.api.models.auth import UserCreate


async def create_user(email: str, password: str, role: str):
    """Create a user and optionally update their role."""
    async with async_session_maker() as session:
        user_db = SQLAlchemyUserDatabase(session, User)
        user_manager = UserManager(user_db)

        # 1. Create user
        user_create = UserCreate(email=email, password=password)
        try:
            user = await user_manager.create(user_create)
            print(f"User created successfully: {user.email} (ID: {user.id})")

            # 2. Update role if not viewer
            if role != UserRole.VIEWER.value:
                try:
                    user_role = UserRole(role)
                    stmt = update(User).where(User.id == user.id).values(role=user_role.value)
                    await session.execute(stmt)
                    await session.commit()
                    print(f"User role updated to: {user_role.value}")
                except ValueError:
                    print(f"Error: Invalid role '{role}'. Defaulting to 'viewer'.")
                    print(f"Available roles: {[r.value for r in UserRole]}")
            else:
                await session.commit()
                print("User role set to: viewer")

        except Exception as e:
            print(f"Error creating user: {e}")
            await session.rollback()


def main():
    parser = argparse.ArgumentParser(description="Create a user account.")
    parser.add_argument("--email", required=True, help="User email")
    parser.add_argument("--password", required=True, help="User password")
    parser.add_argument(
        "--role",
        default="viewer",
        choices=[r.value for r in UserRole],
        help="User role (default: viewer)",
    )

    args = parser.parse_args()

    asyncio.run(create_user(args.email, args.password, args.role))


if __name__ == "__main__":
    main()
