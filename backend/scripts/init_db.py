"""Create a SmartRoute AI SQLite database from the versioned schema."""

from __future__ import annotations

import argparse
from pathlib import Path

from backend.app.database import DEFAULT_DATABASE, initialize_database


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument(
        "--force",
        action="store_true",
        help="replace an existing database (destructive)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    database = args.database.resolve()
    if database.exists():
        if not args.force:
            raise SystemExit(f"Database already exists: {database}. Use --force to replace it.")
        database.unlink()
    created = initialize_database(database)
    print(f"Created SmartRoute AI database: {created}")


if __name__ == "__main__":
    main()

