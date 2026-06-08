"""Database models using SQLite."""
import os, sqlite3, hashlib

DB = None

def get_db(data_dir):
    global DB
    if DB is None:
        DB = os.path.join(data_dir, 'users.db')
    return DB

def init_db(data_dir):
    db_path = get_db(data_dir)
    conn = sqlite3.connect(db_path)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    # Create default admin if not exists
    from werkzeug.security import generate_password_hash
    cur = conn.execute('SELECT id FROM users WHERE username=?', ('admin',))
    if cur.fetchone() is None:
        conn.execute(
            'INSERT INTO users (username, password_hash) VALUES (?, ?)',
            ('admin', generate_password_hash('admin123'))
        )
        conn.commit()
    conn.close()

def verify_user(username, password):
    from werkzeug.security import check_password_hash
    conn = sqlite3.connect(DB)
    cur = conn.execute('SELECT password_hash FROM users WHERE username=?', (username,))
    row = cur.fetchone()
    conn.close()
    if row and check_password_hash(row[0], password):
        return True
    return False

def user_exists(username):
    conn = sqlite3.connect(DB)
    cur = conn.execute('SELECT id FROM users WHERE username=?', (username,))
    exists = cur.fetchone() is not None
    conn.close()
    return exists

def create_user(username, password):
    from werkzeug.security import generate_password_hash
    conn = sqlite3.connect(DB)
    try:
        conn.execute(
            'INSERT INTO users (username, password_hash) VALUES (?, ?)',
            (username, generate_password_hash(password))
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()
