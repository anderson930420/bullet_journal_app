# tests/test_smoke.py
# Smoke tests for Bullet Journal app — non-GUI, headless-safe.
# Target: database init path and capture_service/collections_service entry paths.
# Uses Python stdlib unittest (no pytest dependency required).

import sys
import uuid
import tempfile
import shutil
import unittest
from pathlib import Path

# Ensure the worktree's root is on the path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import after path is set
import database
import services.capture_service as capture_service
import services.collections_service as collections_service


class TestDatabaseInit(unittest.TestCase):
    """Smoke test: init_db() creates tables without error."""

    def setUp(self):
        # Save original DB_PATH and create a temp directory for the test DB
        self._orig_db_path = database.DB_PATH
        self._temp_dir = tempfile.mkdtemp()
        self._temp_db = Path(self._temp_dir) / "test.db"
        # Patch DB_PATH with a Path object (matching the original type)
        database.DB_PATH = self._temp_db

    def tearDown(self):
        # Restore original DB_PATH and clean up temp directory
        database.DB_PATH = self._orig_db_path
        shutil.rmtree(self._temp_dir, ignore_errors=True)

    def test_init_db_runs_without_error(self):
        # Should not raise
        database.init_db()
        # Verify tables exist
        conn = database.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cur.fetchall()}
        conn.close()
        self.assertIn("entries", tables)
        self.assertIn("collections", tables)

    def test_entries_table_has_expected_columns(self):
        database.init_db()
        conn = database.get_connection()
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(entries)")
        columns = {row[1] for row in cur.fetchall()}
        conn.close()
        expected = {"id", "content", "type", "bucket", "completed", "is_deleted",
                    "deleted_at", "sort_order", "created_at", "collection_id"}
        missing = expected - columns
        self.assertFalse(missing, f"Missing columns: {missing}")


class TestCaptureService(unittest.TestCase):
    """Smoke test: capture_service.create_entry and fetch_entries round-trip."""

    def setUp(self):
        self._orig_db_path = database.DB_PATH
        self._temp_dir = tempfile.mkdtemp()
        self._temp_db = Path(self._temp_dir) / "test.db"
        database.DB_PATH = self._temp_db

    def tearDown(self):
        database.DB_PATH = self._orig_db_path
        shutil.rmtree(self._temp_dir, ignore_errors=True)

    def test_create_and_fetch_entry(self):
        database.init_db()
        content = f"smoke-test-entry-{uuid.uuid4().hex[:8]}"
        entry_type = "task"

        capture_service.create_entry(content, entry_type)
        rows = capture_service.fetch_entries()

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][1], content)        # column index 1 = content
        self.assertEqual(rows[0][2], entry_type)    # column index 2 = type

    def test_fetch_entries_returns_empty_list_when_no_entries(self):
        database.init_db()
        rows = capture_service.fetch_entries()
        self.assertEqual(rows, [])

    def test_create_future_entry_and_fetch(self):
        database.init_db()
        content = f"future-entry-{uuid.uuid4().hex[:8]}"
        entry_type = "note"

        capture_service.create_future_entry(content, entry_type)
        future_rows = capture_service.fetch_future_entries()

        self.assertEqual(len(future_rows), 1)
        self.assertEqual(future_rows[0][1], content)


class TestCollectionService(unittest.TestCase):
    """Smoke test: collections_service save and fetch round-trip."""

    def setUp(self):
        self._orig_db_path = database.DB_PATH
        self._temp_dir = tempfile.mkdtemp()
        self._temp_db = Path(self._temp_dir) / "test.db"
        database.DB_PATH = self._temp_db

    def tearDown(self):
        database.DB_PATH = self._orig_db_path
        shutil.rmtree(self._temp_dir, ignore_errors=True)

    def test_create_and_fetch_collection(self):
        database.init_db()
        title = f"smoke-collection-{uuid.uuid4().hex[:8]}"
        content = "test content"

        cid = collections_service.save_collection(None, title, content)
        self.assertIsNotNone(cid)

        fetched = collections_service.fetch_collection(cid)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched[1], title)         # column index 1 = title
        self.assertEqual(fetched[2], content)        # column index 2 = content


class TestSchemaMigrations(unittest.TestCase):
    """Tests for versioned schema migrations."""

    def setUp(self):
        self._orig_db_path = database.DB_PATH
        self._temp_dir = tempfile.mkdtemp()
        self._temp_db = Path(self._temp_dir) / "test_migrate.db"
        database.DB_PATH = self._temp_db

    def tearDown(self):
        database.DB_PATH = self._orig_db_path
        shutil.rmtree(self._temp_dir, ignore_errors=True)

    def test_init_db_records_schema_version(self):
        database.init_db()
        conn = database.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT version FROM schema_version ORDER BY version DESC LIMIT 1")
        row = cur.fetchone()
        conn.close()
        self.assertIsNotNone(row, "schema_version table should have a row")
        self.assertEqual(row[0], 2, "schema_version should be 2 after applying all migrations")

    def test_init_db_idempotent(self):
        # First init
        database.init_db()
        conn1 = database.get_connection()
        cur1 = conn1.cursor()
        cur1.execute("SELECT version FROM schema_version ORDER BY version DESC LIMIT 1")
        v1 = cur1.fetchone()[0]
        conn1.close()

        # Second init should not fail
        database.init_db()
        conn2 = database.get_connection()
        cur2 = conn2.cursor()
        cur2.execute("SELECT version FROM schema_version ORDER BY version DESC LIMIT 1")
        v2 = cur2.fetchone()[0]
        conn2.close()

        self.assertEqual(v1, v2, "schema version should be unchanged after second init_db()")

    def test_schema_version_not_reapplied(self):
        database.init_db()
        conn = database.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM schema_version")
        count_after_first = cur.fetchone()[0]
        conn.close()

        # Second init should not insert new version rows
        database.init_db()
        conn2 = database.get_connection()
        cur2 = conn2.cursor()
        cur2.execute("SELECT COUNT(*) FROM schema_version")
        count_after_second = cur2.fetchone()[0]
        conn2.close()

        self.assertEqual(count_after_first, count_after_second,
                         "second init_db() should not insert additional schema_version rows")

    def test_entries_has_all_expected_columns_after_migration(self):
        database.init_db()
        conn = database.get_connection()
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(entries)")
        columns = {row[1] for row in cur.fetchall()}
        conn.close()
        expected = {"id", "content", "type", "bucket", "completed", "is_deleted",
                    "deleted_at", "sort_order", "created_at", "collection_id"}
        missing = expected - columns
        self.assertFalse(missing, f"Missing columns: {missing}")

    def test_collections_has_all_expected_columns_after_migration(self):
        database.init_db()
        conn = database.get_connection()
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(collections)")
        columns = {row[1] for row in cur.fetchall()}
        conn.close()
        expected = {"id", "title", "content", "is_deleted", "deleted_at", "sort_order", "created_at", "updated_at"}
        missing = expected - columns
        self.assertFalse(missing, f"Missing columns: {missing}")


if __name__ == "__main__":
    unittest.main()