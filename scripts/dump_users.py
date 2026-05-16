import asyncio
import sys
from pathlib import Path
from sqlalchemy import select

# Add project root to sys.path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from src.infrastructure.database.models import User
from src.infrastructure.database.session import async_session_maker

async def dump_users() -> None:
    """Dumps user data from the database using the centralized session."""
    try:
        async with async_session_maker() as session:
            result = await session.execute(select(User))
            users = result.scalars().all()

            print(f"{'ID':<36} | {'Email':<30} | {'Active':<6} | {'Role':<10}")
            print("-" * 90)
            for u in users:
                print(f"{str(u.id):<36} | {u.email:<30} | {str(u.is_active):<6} | {u.role:<10}")

    except Exception as e:
        print(f"Error: Could not dump users. {e}")

if __name__ == '__main__':
    asyncio.run(dump_users())
