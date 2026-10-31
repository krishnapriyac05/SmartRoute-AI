from __future__ import annotations

import unittest
from datetime import UTC, datetime, time
from zoneinfo import ZoneInfo

from backend.app.services.sla import add_business_minutes


class SlaServiceTests(unittest.TestCase):
    def test_business_deadline_skips_weekend(self) -> None:
        zone = ZoneInfo("Asia/Kolkata")
        started = datetime(2026, 10, 30, 17, 0, tzinfo=zone)  # Friday
        hours = {day: [(time(9), time(18))] for day in range(5)}
        deadline = add_business_minutes(started, 120, "Asia/Kolkata", hours)
        self.assertEqual(deadline, datetime(2026, 11, 2, 10, 0, tzinfo=zone))

    def test_business_deadline_moves_after_hours_to_open(self) -> None:
        zone = ZoneInfo("Asia/Kolkata")
        started = datetime(2026, 10, 29, 20, 0, tzinfo=zone)
        deadline = add_business_minutes(started, 60, "Asia/Kolkata", {3: [(time(9), time(18))], 4: [(time(9), time(18))]})
        self.assertEqual(deadline, datetime(2026, 10, 30, 10, 0, tzinfo=zone))

    def test_24x7_policy_uses_elapsed_minutes(self) -> None:
        started = datetime(2026, 10, 31, 23, 30, tzinfo=UTC)
        self.assertEqual(add_business_minutes(started, 90, "UTC", {}, is_24x7=True),
                         datetime(2026, 11, 1, 1, 0, tzinfo=UTC))

    def test_naive_timestamp_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            add_business_minutes(datetime(2026, 1, 1), 60, "UTC", {3: [(time(9), time(18))]})


if __name__ == "__main__":
    unittest.main()

