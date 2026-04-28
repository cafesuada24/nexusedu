import sqlite3

def dump_users():
    conn = sqlite3.connect('auth.db')
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id, email, is_active, role FROM user")
        users = cursor.fetchall()
        print("ID | Email | Active | Role")
        for u in users:
            print(f"{u[0]} | {u[1]} | {u[2]} | {u[3]}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    dump_users()
