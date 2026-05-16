#!/bin/bash
set -e

# Change to project root if script is run from scripts/ directory
cd "$(dirname "$0")/.."

echo "Initializing database reseed process..."

# 1. Environment Check and Confirmation
uv run python -c "
from scripts.utils import is_production
import sys

if is_production():
    print('\n' + '!' * 60)
    print('CRITICAL WARNING: YOU ARE RUNNING AGAINST A PRODUCTION DATABASE.')
    print('THIS OPERATION WILL WIPE ALL DATA IN THE PUBLIC SCHEMA.')
    print('!' * 60 + '\n')
    try:
        response = input('Are you absolutely sure you want to proceed? [y/N]: ').lower()
        if response not in ('y', 'yes'):
            print('Action cancelled.')
            sys.exit(1)
    except EOFError:
        print('\nNo input detected. Action cancelled for safety.')
        sys.exit(1)
"

# 2. Force Wipe Database Schema
echo "Wiping database schema (force-terminating active connections)..."
uv run python -c "
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from src.core.config import config

async def wipe_db():
    # Use isolation_level='AUTOCOMMIT' for dropping the schema
    # We create a temporary engine to avoid pooling issues during the wipe
    url = config.database_url
    if 'postgresql+asyncpg' not in url:
        # Ensure we use the asyncpg driver if not specified
        url = url.replace('postgresql://', 'postgresql+asyncpg://')
    
    engine = create_async_engine(url, isolation_level='AUTOCOMMIT')
    async with engine.connect() as conn:
        print('Terminating other active database connections to release locks...')
        try:
            await conn.execute(text(\"\"\"
                SELECT pg_terminate_backend(pg_stat_activity.pid)
                FROM pg_stat_activity
                WHERE pg_stat_activity.datname = current_database() 
                AND pid <> pg_backend_pid();
            \"\"\"))
        except Exception as e:
            print(f'Warning: Could not terminate connections (might lack permissions): {e}')
        
        print('Dropping and recreating public schema...')
        await conn.execute(text('DROP SCHEMA IF EXISTS public CASCADE;'))
        await conn.execute(text('CREATE SCHEMA public;'))
        await conn.execute(text('GRANT ALL ON SCHEMA public TO public;'))
        
    await engine.dispose()

try:
    import sys
    asyncio.run(wipe_db())
except Exception as e:
    print(f'Error during database wipe: {e}')
    sys.exit(1)
"

# 3. Rebuild Schema with Migrations
echo "Rebuilding database schema with Alembic migrations..."
uv run alembic upgrade head

# 4. Seed Data
echo "Seeding initial data..."
uv run python scripts/seed_data.py

echo ""
echo "===================================================="
echo "SUCCESS: Database has been reseeded and migrated."
echo "===================================================="
