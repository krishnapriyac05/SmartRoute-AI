"""Calendar-aware SLA deadline calculations."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo


def add_business_minutes(
    started_at: datetime,
    minutes: int,
    timezone: str,
    weekly_hours: dict[int, list[tuple[time, time]]],
    exceptions: dict[date, list[tuple[time, time]] | None] | None = None,
    is_24x7: bool = False,
) -> datetime:
    """Add working minutes and return a deadline in the input timezone/UTC frame."""
    if minutes <= 0:
        raise ValueError("SLA minutes must be positive")
    original_tz = started_at.tzinfo
    if original_tz is None:
        raise ValueError("started_at must be timezone-aware")
    if is_24x7:
        return started_at + timedelta(minutes=minutes)
    zone = ZoneInfo(timezone)
    current = started_at.astimezone(zone)
    remaining = minutes
    exceptions = exceptions or {}
    while remaining > 0:
        day = current.date()
        windows = exceptions.get(day, weekly_hours.get(day.weekday(), []))
        windows = windows or []
        progressed = False
        for opens, closes in windows:
            window_start = datetime.combine(day, opens, zone)
            window_end = datetime.combine(day, closes, zone)
            if current >= window_end:
                continue
            if current < window_start:
                current = window_start
            available = int((window_end - current).total_seconds() // 60)
            if available <= 0:
                continue
            progressed = True
            if remaining <= available:
                return (current + timedelta(minutes=remaining)).astimezone(original_tz)
            remaining -= available
            current = window_end
        current = datetime.combine(day + timedelta(days=1), time.min, zone)
        if not progressed and not weekly_hours and not exceptions:
            raise ValueError("Business calendar has no working windows")
    return current.astimezone(original_tz)


def deadline_from_database(connection, channel_id: str, priority: str, started_at: datetime, target: str) -> datetime:
    """Resolve the effective SLA policy/calendar and calculate its deadline."""
    policy = connection.execute("""SELECT sp.*,bc.timezone,bc.is_24x7 FROM sla_policies sp
        JOIN business_calendars bc ON bc.calendar_id=sp.calendar_id
        WHERE sp.channel_id=? AND sp.priority=? AND sp.effective_from<=?
        AND (sp.effective_to IS NULL OR sp.effective_to>?) ORDER BY sp.effective_from DESC LIMIT 1""",
        (channel_id, priority, started_at.isoformat(), started_at.isoformat())).fetchone()
    if policy is None:
        raise ValueError("No effective SLA policy")
    duration = policy["first_response_minutes" if target == "FIRST_RESPONSE" else "resolution_minutes"]
    hours: dict[int, list[tuple[time, time]]] = {}
    for row in connection.execute("SELECT weekday,opens_at,closes_at FROM calendar_hours WHERE calendar_id=?", (policy["calendar_id"],)):
        hours.setdefault(row["weekday"], []).append((time.fromisoformat(row["opens_at"]), time.fromisoformat(row["closes_at"])))
    exception_rows = connection.execute("SELECT * FROM calendar_exceptions WHERE calendar_id=?", (policy["calendar_id"],)).fetchall()
    exceptions = {date.fromisoformat(row["exception_date"]): None if row["is_closed"] else
                  [(time.fromisoformat(row["opens_at"]), time.fromisoformat(row["closes_at"]))] for row in exception_rows}
    return add_business_minutes(started_at, duration, policy["timezone"], hours, exceptions, bool(policy["is_24x7"]))

