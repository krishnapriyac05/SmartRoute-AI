from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from backend.app.database import connect
from backend.generator.generate import DEFAULT_SEED, PROFILES, generate


class GeneratorTests(unittest.TestCase):
    def test_starter_counts_and_integrity(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            database = root / "starter.db"
            manifest = generate("starter", database, root / "exports", DEFAULT_SEED)
            self.assertEqual(manifest["counts"]["agents"], PROFILES["starter"].agents)
            self.assertEqual(manifest["counts"]["tickets"], PROFILES["starter"].tickets)
            self.assertEqual(manifest["counts"]["messages"], PROFILES["starter"].messages)
            connection = connect(database)
            try:
                self.assertEqual(connection.execute("PRAGMA foreign_key_check").fetchall(), [])
                unsafe = connection.execute("""SELECT COUNT(*) FROM tickets t JOIN intents i ON i.intent_id=t.intent_id
                    WHERE i.safety_critical=1 AND t.priority<>'CRITICAL'""").fetchone()[0]
                self.assertEqual(unsafe, 0)
                skill_mismatches = connection.execute("""SELECT COUNT(*) FROM tickets t
                    JOIN intents i ON i.intent_id=t.intent_id
                    WHERE NOT EXISTS (SELECT 1 FROM agent_skills s
                        WHERE s.agent_id=t.assigned_agent_id AND s.skill_id=i.required_skill_id)""").fetchone()[0]
                language_mismatches = connection.execute("""SELECT COUNT(*) FROM tickets t
                    WHERE NOT EXISTS (SELECT 1 FROM agent_languages l
                        WHERE l.agent_id=t.assigned_agent_id AND l.language_id=t.language_id)""").fetchone()[0]
                self.assertEqual(skill_mismatches, 0)
                self.assertEqual(language_mismatches, 0)
                capacity_violations = connection.execute("""SELECT COUNT(*) FROM agents a WHERE
                    (SELECT COUNT(*) FROM tickets t WHERE t.assigned_agent_id=a.agent_id
                     AND t.status IN ('ASSIGNED','IN_PROGRESS','PENDING_CUSTOMER','ESCALATED','REOPENED')) > a.concurrency_limit""").fetchone()[0]
                self.assertEqual(capacity_violations, 0)
            finally:
                connection.close()

    def test_same_seed_has_identical_exports(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first = generate("starter", root / "one.db", root / "one", DEFAULT_SEED)
            second = generate("starter", root / "two.db", root / "two", DEFAULT_SEED)
            self.assertEqual(first["files"], second["files"])
            self.assertEqual(first["counts"], second["counts"])

    def test_full_profile_has_required_volume(self) -> None:
        profile = PROFILES["full"]
        self.assertEqual((profile.tickets, profile.agents, profile.messages, profile.days),
                         (30_000, 100, 100_000, 90))


if __name__ == "__main__":
    unittest.main()

