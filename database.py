import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path("bullet_journal.db")


@contextmanager
def _with_connection():
    """Exception-safe connection context manager.

    Automatically commits on success, rolls back on exception,
    and always closes the connection.
    """
    conn = sqlite3.connect(DB_PATH)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_connection():
    """Return a raw connection. Caller is responsible for closing it.

    Kept for backward compatibility with tests and external callers
    who need direct connection access.
    """
    return sqlite3.connect(DB_PATH)


def _get_schema_version(conn):
    """Read current schema version from schema_version table."""
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT version FROM schema_version ORDER BY version DESC LIMIT 1")
    except sqlite3.OperationalError:
        return 0
    row = cursor.fetchone()
    return row[0] if row else 0


def _set_schema_version(conn, version):
    """Record a schema version in the schema_version table."""
    cursor = conn.cursor()
    cursor.execute("INSERT INTO schema_version (version) VALUES (?)", (version,))


# Ordered migrations: (version, description)
# Version 0 = bare base tables (entries, collections) with no extra columns.
_MIGRATIONS = [
    # Version 1: Add entries columns (collection_id, is_deleted, deleted_at, sort_order)
    (1, "add entries columns"),
    # Version 2: Add collections columns (content, is_deleted, deleted_at, updated_at, sort_order)
    (2, "add collections columns"),
]


def _run_migrations(conn, from_version):
    """Apply all pending migrations greater than from_version."""
    for version, description in _MIGRATIONS:
        if version > from_version:
            if version == 1:
                _migration_1_add_entries_columns(conn)
            elif version == 2:
                _migration_2_add_collections_columns(conn)
            _set_schema_version(conn, version)


def _migration_1_add_entries_columns(conn):
    """Add collection_id, is_deleted, deleted_at, sort_order to entries."""
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(entries)")
    columns = [row[1] for row in cursor.fetchall()]

    if "collection_id" not in columns:
        cursor.execute("ALTER TABLE entries ADD COLUMN collection_id INTEGER")

    if "is_deleted" not in columns:
        cursor.execute("ALTER TABLE entries ADD COLUMN is_deleted INTEGER DEFAULT 0")

    if "deleted_at" not in columns:
        cursor.execute("ALTER TABLE entries ADD COLUMN deleted_at TIMESTAMP")

    if "sort_order" not in columns:
        cursor.execute("ALTER TABLE entries ADD COLUMN sort_order INTEGER")

    # Backfill sort_order for existing rows
    cursor.execute(
        "SELECT id, bucket FROM entries WHERE sort_order IS NULL ORDER BY bucket, id DESC"
    )
    entry_rows = cursor.fetchall()
    bucket_positions = {}
    for entry_id, bucket in entry_rows:
        position = bucket_positions.get(bucket, 0)
        cursor.execute(
            "UPDATE entries SET sort_order = ? WHERE id = ?",
            (position, entry_id)
        )
        bucket_positions[bucket] = position + 1


def _migration_2_add_collections_columns(conn):
    """Add content, is_deleted, deleted_at, updated_at, sort_order to collections."""
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(collections)")
    collection_columns = [row[1] for row in cursor.fetchall()]

    if "content" not in collection_columns:
        cursor.execute("ALTER TABLE collections ADD COLUMN content TEXT DEFAULT ''")

    if "is_deleted" not in collection_columns:
        cursor.execute("ALTER TABLE collections ADD COLUMN is_deleted INTEGER DEFAULT 0")

    if "deleted_at" not in collection_columns:
        cursor.execute("ALTER TABLE collections ADD COLUMN deleted_at TIMESTAMP")

    if "updated_at" not in collection_columns:
        cursor.execute("ALTER TABLE collections ADD COLUMN updated_at TIMESTAMP")

    if "sort_order" not in collection_columns:
        cursor.execute("ALTER TABLE collections ADD COLUMN sort_order INTEGER")

    # Backfill sort_order for existing rows
    cursor.execute(
        "SELECT id FROM collections WHERE sort_order IS NULL ORDER BY updated_at DESC, id DESC"
    )
    collection_rows = cursor.fetchall()
    for position, (collection_id,) in enumerate(collection_rows):
        cursor.execute(
            "UPDATE collections SET sort_order = ? WHERE id = ?",
            (position, collection_id)
        )


def init_db():
    """Initialize or migrate the database schema.

    Creates base tables, then applies pending versioned migrations.
    Safe to call repeatedly — already-applied migrations are skipped.
    """
    with _with_connection() as conn:
        # Create base tables (version 0)
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            type TEXT NOT NULL,
            bucket TEXT DEFAULT 'today',
            collection_id INTEGER,
            completed INTEGER DEFAULT 0,
            is_deleted INTEGER DEFAULT 0,
            deleted_at TIMESTAMP,
            sort_order INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS collections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT DEFAULT '',
            is_deleted INTEGER DEFAULT 0,
            deleted_at TIMESTAMP,
            sort_order INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # Ensure schema_version table exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS schema_version (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                version INTEGER NOT NULL,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Read current version and apply pending migrations
        current_version = _get_schema_version(conn)
        _run_migrations(conn, current_version)


# ── Entries ──────────────────────────────────────────────────────────────────

def add_entry(content, entry_type, bucket="today"):
    with _with_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT MIN(sort_order) FROM entries WHERE bucket = ? AND is_deleted = 0",
            (bucket,)
        )
        min_order = cursor.fetchone()[0]
        sort_order = 0 if min_order is None else min_order - 1

        cursor.execute(
            "INSERT INTO entries (content, type, bucket, sort_order) VALUES (?, ?, ?, ?)",
            (content, entry_type, bucket, sort_order)
        )


def get_entries():
    with _with_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, content, type, completed FROM entries WHERE bucket = 'today' AND is_deleted = 0 ORDER BY sort_order ASC, id DESC"
        )
        return cursor.fetchall()


def update_entry_completed(entry_id, completed):
    with _with_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE entries SET completed = ? WHERE id = ?",
            (completed, entry_id)
        )


def delete_entry(entry_id):
    with _with_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE entries SET is_deleted = 1, deleted_at = CURRENT_TIMESTAMP WHERE id = ?",
            (entry_id,)
        )


def migrate_entry(entry_id, bucket):
    with _with_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE entries SET bucket = ? WHERE id = ?",
            (bucket, entry_id)
        )


def migrate_to_future(entry_id):
    migrate_entry(entry_id, "future")


def get_future_entries():
    with _with_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, content, type, completed FROM entries WHERE bucket = 'future' AND is_deleted = 0 ORDER BY sort_order ASC, id DESC"
        )
        return cursor.fetchall()


def get_monthly_entries():
    with _with_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, content, type, completed FROM entries WHERE bucket = 'monthly' AND is_deleted = 0 ORDER BY sort_order ASC, id DESC"
        )
        return cursor.fetchall()


# ── Collections ──────────────────────────────────────────────────────────────

def add_collection(title, content=""):
    with _with_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT MIN(sort_order) FROM collections WHERE is_deleted = 0"
        )
        min_order = cursor.fetchone()[0]
        sort_order = 0 if min_order is None else min_order - 1

        cursor.execute(
            "INSERT INTO collections (title, content, updated_at, sort_order) VALUES (?, ?, CURRENT_TIMESTAMP, ?)",
            (title, content, sort_order)
        )
        return cursor.lastrowid


def get_collections():
    with _with_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, title FROM collections WHERE is_deleted = 0 ORDER BY sort_order ASC, id DESC"
        )
        return cursor.fetchall()


def get_collection(collection_id):
    with _with_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, title, content FROM collections WHERE id = ? AND is_deleted = 0",
            (collection_id,)
        )
        return cursor.fetchone()


def update_collection(collection_id, title, content):
    with _with_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE collections SET title = ?, content = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (title, content, collection_id)
        )


# ── Deleted / Restore ────────────────────────────────────────────────────────

def get_deleted_entries():
    with _with_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, content, type, completed, bucket, 'entry' AS kind, deleted_at
            FROM entries
            WHERE is_deleted = 1
            UNION ALL
            SELECT id, title AS content, 'note' AS type, 0 AS completed, 'collections' AS bucket, 'collection' AS kind, deleted_at
            FROM collections
            WHERE is_deleted = 1
            ORDER BY deleted_at DESC, id DESC
            """
        )
        return cursor.fetchall()


def restore_entry(entry_id):
    with _with_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE entries SET is_deleted = 0, deleted_at = NULL WHERE id = ?",
            (entry_id,)
        )


def permanently_delete_entry(entry_id):
    with _with_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM entries WHERE id = ? AND is_deleted = 1",
            (entry_id,)
        )


def delete_collection(collection_id):
    with _with_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE collections SET is_deleted = 1, deleted_at = CURRENT_TIMESTAMP WHERE id = ?",
            (collection_id,)
        )


def restore_collection(collection_id):
    with _with_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE collections SET is_deleted = 0, deleted_at = NULL WHERE id = ?",
            (collection_id,)
        )


def permanently_delete_collection(collection_id):
    with _with_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM collections WHERE id = ? AND is_deleted = 1",
            (collection_id,)
        )


# ── Ordering ──────────────────────────────────────────────────────────────────

def update_entry_order(bucket, entry_ids):
    with _with_connection() as conn:
        cursor = conn.cursor()
        for position, entry_id in enumerate(entry_ids):
            cursor.execute(
                "UPDATE entries SET sort_order = ? WHERE id = ? AND bucket = ?",
                (position, entry_id, bucket)
            )


def update_collection_order(collection_ids):
    with _with_connection() as conn:
        cursor = conn.cursor()
        for position, collection_id in enumerate(collection_ids):
            cursor.execute(
                "UPDATE collections SET sort_order = ? WHERE id = ?",
                (position, collection_id)
            )
