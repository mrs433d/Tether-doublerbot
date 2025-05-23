import sqlite3

conn = sqlite3.connect("users.db", check_same_thread=False)
c = conn.cursor()

def init_db():
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        balance REAL DEFAULT 0,
        invited_by INTEGER,
        referrals INTEGER DEFAULT 0
    )""")
    conn.commit()

def add_user(user_id, invited_by=None):
    c.execute("SELECT id FROM users WHERE id = ?", (user_id,))
    if not c.fetchone():
        c.execute("INSERT INTO users (id, invited_by) VALUES (?, ?)", (user_id, invited_by))
        if invited_by:
            c.execute("UPDATE users SET balance = balance + 0.5, referrals = referrals + 1 WHERE id = ?", (invited_by,))
        conn.commit()

def update_balance(user_id, amount):
    c.execute("UPDATE users SET balance = balance + ? WHERE id = ?", (amount, user_id))
    conn.commit()

def get_balance(user_id):
    c.execute("SELECT balance FROM users WHERE id = ?", (user_id,))
    result = c.fetchone()
    return result[0] if result else 0
