from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from backend.app.database import connect
from backend.app.services.validation import validate
from backend.generator.anomalies import inject
from backend.generator.generate import DEFAULT_SEED, generate


class AnomalyTests(unittest.TestCase):
    def test_clean_baseline_has_no_mandatory_anomalies(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            database = root / "clean.db"
            generate("starter", database, root / "exports", DEFAULT_SEED)
            connection = connect(database)
            try:
                report = validate(connection)
            finally:
                connection.close()
            self.assertTrue(report["passed"], report["findings"])
            self.assertEqual(report["findingCount"], 0)

    def test_all_five_injected_anomalies_are_detected_independently(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            clean, evaluation = root / "clean.db", root / "evaluation.db"
            generate("starter", clean, root / "exports", DEFAULT_SEED)
            injected = inject(clean, evaluation)
            connection = connect(evaluation)
            try:
                report = validate(connection)
                ground_truth = {(row["anomaly_type"], row["entity_id"]) for row in connection.execute(
                    "SELECT anomaly_type,entity_id FROM anomaly_ground_truth")}
            finally:
                connection.close()
            expected_types = {"CAPACITY_EXCEEDED", "SLA_CALENDAR_IGNORED", "REOPEN_HISTORY_LOST",
                              "TRANSFER_LOOP", "SAFETY_PRIORITY_CONTRADICTION"}
            self.assertEqual({item["type"] for item in injected}, expected_types)
            detected = {(item["type"], item["entityId"]) for item in report["findings"]}
            self.assertEqual(detected, ground_truth)
            self.assertEqual(report["findingCount"], 5)
            self.assertFalse(report["passed"])


if __name__ == "__main__":
    unittest.main()

