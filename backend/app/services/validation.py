"""Independent integrity and anomaly validators (never reads ground truth)."""

from __future__ import annotations

from datetime import datetime

from backend.app.services.sla import deadline_from_database


def finding(anomaly_type: str, entity_type: str, entity_id: str, evidence: dict) -> dict:
    return {"type": anomaly_type, "entityType": entity_type, "entityId": entity_id, "evidence": evidence}


def detect_capacity(connection) -> list[dict]:
    rows = connection.execute("""SELECT a.agent_id,a.concurrency_limit,COUNT(t.ticket_id) active_count
        FROM agents a JOIN tickets t ON t.assigned_agent_id=a.agent_id
        AND t.status IN ('ASSIGNED','IN_PROGRESS','PENDING_CUSTOMER','ESCALATED','REOPENED')
        GROUP BY a.agent_id HAVING COUNT(t.ticket_id)>a.concurrency_limit""").fetchall()
    return [finding("CAPACITY_EXCEEDED", "agent", row["agent_id"],
                    {"activeTickets": row["active_count"], "limit": row["concurrency_limit"]}) for row in rows]


def detect_sla_calendar(connection) -> list[dict]:
    results = []
    rows = connection.execute("SELECT ticket_id,channel_id,priority,created_at,resolution_due_at FROM tickets").fetchall()
    for row in rows:
        started = datetime.fromisoformat(row["created_at"].replace("Z", "+00:00"))
        expected = deadline_from_database(connection, row["channel_id"], row["priority"], started, "RESOLUTION")
        actual = datetime.fromisoformat(row["resolution_due_at"].replace("Z", "+00:00"))
        if expected != actual:
            results.append(finding("SLA_CALENDAR_IGNORED", "ticket", row["ticket_id"],
                                   {"actual": row["resolution_due_at"], "expected": expected.isoformat()}))
    return results


def detect_reopen_history(connection) -> list[dict]:
    rows = connection.execute("""SELECT t.ticket_id FROM tickets t WHERE t.status='REOPENED'
        AND NOT EXISTS (SELECT 1 FROM ticket_events e WHERE e.ticket_id=t.ticket_id AND e.event_type='REOPENED')""").fetchall()
    return [finding("REOPEN_HISTORY_LOST", "ticket", row["ticket_id"], {"currentStatus": "REOPENED"}) for row in rows]


def detect_transfer_loops(connection) -> list[dict]:
    results = []
    tickets = connection.execute("SELECT DISTINCT ticket_id FROM assignment_events WHERE event_type='TRANSFERRED'").fetchall()
    for ticket in tickets:
        pairs = [(row["from_agent_id"], row["to_agent_id"]) for row in connection.execute(
            "SELECT from_agent_id,to_agent_id FROM assignment_events WHERE ticket_id=? AND event_type='TRANSFERRED' ORDER BY sequence_no",
            (ticket["ticket_id"],)).fetchall()]
        for index in range(len(pairs) - 3):
            a, b, c, d = pairs[index:index + 4]
            if a[0] and a[1] and a == c and b == d and a == (b[1], b[0]):
                results.append(finding("TRANSFER_LOOP", "ticket", ticket["ticket_id"], {"cycle": [a, b, c, d]}))
                break
    return results


def detect_safety_priority(connection) -> list[dict]:
    rows = connection.execute("""SELECT t.ticket_id,t.priority,i.code intent FROM tickets t
        JOIN intents i ON i.intent_id=t.intent_id WHERE i.safety_critical=1 AND t.priority<>'CRITICAL'""").fetchall()
    return [finding("SAFETY_PRIORITY_CONTRADICTION", "ticket", row["ticket_id"],
                    {"priority": row["priority"], "intent": row["intent"]}) for row in rows]


def validate(connection) -> dict:
    findings = (detect_capacity(connection) + detect_sla_calendar(connection) + detect_reopen_history(connection)
                + detect_transfer_loops(connection) + detect_safety_priority(connection))
    foreign_keys = [dict(row) for row in connection.execute("PRAGMA foreign_key_check").fetchall()]
    return {"passed": not findings and not foreign_keys, "findingCount": len(findings),
            "findings": sorted(findings, key=lambda item: (item["type"], item["entityId"])),
            "foreignKeyViolations": foreign_keys}

