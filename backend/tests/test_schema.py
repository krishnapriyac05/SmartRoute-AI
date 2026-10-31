from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from backend.app.database import connect, initialize_database


class SchemaTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = Path(self.temp_dir.name) / "test.db"
        initialize_database(self.database)
        self.connection = connect(self.database)

    def tearDown(self) -> None:
        self.connection.close()
        self.temp_dir.cleanup()

    def test_required_core_tables_exist(self) -> None:
        expected = {
            "customers", "channels", "tickets", "messages", "intents",
            "languages", "priority_rules", "agents", "skills", "queues",
            "assignment_events", "sla_events", "resolutions",
        }
        rows = self.connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
        self.assertTrue(expected.issubset({row["name"] for row in rows}))

    def test_foreign_keys_are_enabled_and_schema_is_valid(self) -> None:
        self.assertEqual(self.connection.execute("PRAGMA foreign_keys").fetchone()[0], 1)
        self.assertEqual(self.connection.execute("PRAGMA foreign_key_check").fetchall(), [])

    def test_agent_id_format_is_enforced(self) -> None:
        with self.assertRaises(sqlite3.IntegrityError):
            self.connection.execute(
                """INSERT INTO agents
                (agent_id, full_name, email, timezone, concurrency_limit, status, hired_at)
                VALUES ('BAD-1', 'Test Agent', 'agent@example.test', 'Asia/Kolkata', 5, 'AVAILABLE', '2026-01-01T00:00:00Z')"""
            )

    def test_event_history_is_immutable(self) -> None:
        triggers = self.connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'trigger'"
        ).fetchall()
        names = {row["name"] for row in triggers}
        self.assertIn("prevent_assignment_event_update", names)
        self.assertIn("prevent_ticket_event_delete", names)
        self.assertIn("prevent_sla_event_update", names)

    def test_initialization_is_idempotent(self) -> None:
        initialize_database(self.database)
        count = self.connection.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type = 'table' AND name = 'tickets'"
        ).fetchone()[0]
        self.assertEqual(count, 1)


if __name__ == "__main__":
    unittest.main()

