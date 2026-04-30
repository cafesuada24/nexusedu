import sqlite3
import sys

def dump_users() -> None:
    """Dumps user data from the local SQLite database."""
    # Defaults to data/app.db in the new architecture
    db_path = 'data/app.db'
    
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
