"""Run independent SmartRoute validators and optionally compare separate labels."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from backend.app.database import connect
from backend.app.services.validation import validate


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=Path("data/starter/smartroute.db"))
    parser.add_argument("--compare-ground-truth", action="store_true")
    args = parser.parse_args()
    connection = connect(args.database)
    try:
        report = validate(connection)
        if args.compare_ground_truth:
            expected = {(row["anomaly_type"], row["entity_id"]) for row in connection.execute(
                "SELECT anomaly_type,entity_id FROM anomaly_ground_truth WHERE expected_detection=1")}
            actual = {(item["type"], item["entityId"]) for item in report["findings"]}
            report["comparison"] = {"expected": len(expected), "detected": len(actual),
                                    "truePositives": len(expected & actual),
                                    "falseNegatives": sorted(expected - actual), "falsePositives": sorted(actual - expected)}
    finally:
        connection.close()
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

