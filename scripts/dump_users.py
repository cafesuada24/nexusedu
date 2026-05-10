import os
import sqlite3
import sys
from urllib.parse import urlparse


def dump_users() -> None:
    """Dumps user data from the local SQLite database."""
    # Respect DATABASE_URL if set, otherwise default to data/app.db
    db_url = os.environ.get('DATABASE_URL', 'sqlite+aiosqlite:///./data/app.db')

    # Parse the SQLite path from the URL
    if db_url.startswith('sqlite'):
        # Handle sqlite+aiosqlite:///./data/app.db or sqlite:///data/app.db
        db_path = db_url.split('///')[-1]
        if db_path.startswith('./'):
            db_path = db_path[2:]
    else:
        print(f"Error: DATABASE_URL {db_url} is not a SQLite database.")
        return

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT id, email, is_active, role FROM user')
        users = cursor.fetchall()

        print('ID | Email | Active | Role')
        print('-' * 60)
        for u in users:
            print(f'{u[0]} | {u[1]} | {u[2]} | {u[3]}')

    except sqlite3.OperationalError as e:
        print(f'Error: Could not open database at {db_path}. Ensure it exists.')
        print(f'Details: {e}')
    except Exception as e:
        print(f'An unexpected error occurred: {e}')
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == '__main__':
    dump_users()
