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
        collection_id INTEGER,
        completed INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS collections (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        content TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("PRAGMA table_info(entries)")
    columns = [row[1] for row in cursor.fetchall()]

    if "collection_id" not in columns:
        cursor.execute("ALTER TABLE entries ADD COLUMN collection_id INTEGER")

    cursor.execute("PRAGMA table_info(collections)")
    collection_columns = [row[1] for row in cursor.fetchall()]

    if "content" not in collection_columns:
        cursor.execute("ALTER TABLE collections ADD COLUMN content TEXT DEFAULT ''")

    if "updated_at" not in collection_columns:
        cursor.execute("ALTER TABLE collections ADD COLUMN updated_at TIMESTAMP")

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


def add_collection(title, content=""):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO collections (title, content, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
        (title, content)
    )

    collection_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return collection_id


def get_collections():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id, title FROM collections ORDER BY updated_at DESC, id DESC"
    )

    rows = cursor.fetchall()
    conn.close()

    return rows


def get_collection(collection_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id, title, content FROM collections WHERE id = ?",
        (collection_id,)
    )

    row = cursor.fetchone()
    conn.close()

    return row


def update_collection(collection_id, title, content):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE collections SET title = ?, content = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (title, content, collection_id)
    )

    conn.commit()
    conn.close()
