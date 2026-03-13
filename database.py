import sqlite3
from pathlib import Path

DB_PATH = Path("bullet_journal.db")


def get_connection():
    return sqlite3.connect(DB_PATH)


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS entries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        content TEXT NOT NULL,
        type TEXT NOT NULL,
        bucket TEXT DEFAULT 'today',
        completed INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()

def add_entry(content, entry_type):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO entries (content, type, bucket) VALUES (?, ?, 'today')",
        (content, entry_type)
    )

    conn.commit()
    conn.close()


def get_entries():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id, content, type, completed FROM entries WHERE bucket = 'today' ORDER BY id DESC"
    )

    rows = cursor.fetchall()
    conn.close()

    return rows

def update_entry_completed(entry_id, completed):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE entries SET completed = ? WHERE id = ?",
        (completed, entry_id)
    )

    conn.commit()
    conn.close()

def delete_entry(entry_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM entries WHERE id = ?",
        (entry_id,)
    )

    conn.commit()
    conn.close()

def migrate_entry(entry_id, bucket):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE entries SET bucket = ? WHERE id = ?",
        (bucket, entry_id)
    )

    conn.commit()
    conn.close()

def migrate_to_future(entry_id):
    migrate_entry(entry_id, "future")

def get_future_entries():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id, content, type, completed FROM entries WHERE bucket = 'future' ORDER BY id DESC"
    )

    rows = cursor.fetchall()
    conn.close()

    return rows


def get_monthly_entries():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id, content, type, completed FROM entries WHERE bucket = 'monthly' ORDER BY id DESC"
    )

    rows = cursor.fetchall()
    conn.close()

    return rows
