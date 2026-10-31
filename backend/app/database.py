"""SQLite connection and schema initialization helpers."""

from __future__ import annotations

import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATABASE = PROJECT_ROOT / "backend" / "data" / "smartroute.db"
SCHEMA_FILE = PROJECT_ROOT / "backend" / "schema.sql"


def connect(database: str | Path = DEFAULT_DATABASE) -> sqlite3.Connection:
    """Open a SQLite connection with relational-integrity settings enabled."""
    database_path = Path(database)
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA journal_mode = WAL")
    return connection


def initialize_database(database: str | Path = DEFAULT_DATABASE) -> Path:
    """Create all schema objects in *database* and return its resolved path."""
    database_path = Path(database).resolve()
    schema = SCHEMA_FILE.read_text(encoding="utf-8")
    connection = connect(database_path)
    try:
        connection.executescript(schema)
        connection.commit()
    finally:
        connection.close()
    return database_path
