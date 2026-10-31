"""Transactional, append-only ticket lifecycle operations."""

from __future__ import annotations

import json
from datetime import UTC, datetime


def utc_text(value: datetime | None = None) -> str:
    value = value or datetime.now(UTC)
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def next_sequence(connection, table: str, ticket_id: str) -> int:
    return connection.execute(f"SELECT COALESCE(MAX(sequence_no),0)+1 FROM {table} WHERE ticket_id=?", (ticket_id,)).fetchone()[0]


def append_ticket_event(connection, ticket_id: str, event_type: str, previous: str | None, new: str | None,
                        actor_type: str, actor_id: str | None, reason: str, at: datetime | None = None) -> str:
    sequence = next_sequence(connection, "ticket_events", ticket_id)
    event_id = f"EVT-{ticket_id}-{sequence:03d}"
    connection.execute("INSERT INTO ticket_events VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (event_id, ticket_id, sequence, event_type, previous, new, utc_text(at), actor_type, actor_id, reason, "{}"))
    return event_id


def change_status(connection, ticket_id: str, new_status: str, event_type: str, actor_type: str,
                  actor_id: str | None, reason: str, allowed_from: set[str], at: datetime | None = None) -> str:
    ticket = connection.execute("SELECT status,version FROM tickets WHERE ticket_id=?", (ticket_id,)).fetchone()
    if ticket is None:
        raise ValueError("Ticket not found")
    if ticket["status"] not in allowed_from:
        raise ValueError(f"Cannot change {ticket['status']} to {new_status}")
    timestamp = utc_text(at)
    extra = ", resolved_at=?" if new_status == "RESOLVED" else ""
    parameters = (new_status, timestamp, ticket["version"] + 1, ticket_id, ticket["version"]) if extra else (new_status, ticket["version"] + 1, ticket_id, ticket["version"])
    sql = f"UPDATE tickets SET status=?{extra}, version=? WHERE ticket_id=? AND version=?"
    if connection.execute(sql, parameters).rowcount != 1:
        raise ValueError("Ticket was modified concurrently")
    return append_ticket_event(connection, ticket_id, event_type, ticket["status"], new_status, actor_type, actor_id, reason, at)


def transfer(connection, ticket_id: str, to_agent_id: str, actor_id: str, reason: str, decision: dict,
             at: datetime | None = None) -> str:
    ticket = connection.execute("SELECT assigned_agent_id,queue_id,status,version FROM tickets WHERE ticket_id=?", (ticket_id,)).fetchone()
    if ticket is None:
        raise ValueError("Ticket not found")
    if ticket["assigned_agent_id"] == to_agent_id:
        raise ValueError("Ticket is already assigned to this agent")
    sequence = next_sequence(connection, "assignment_events", ticket_id)
    event_id = f"ASN-{ticket_id}-{sequence:03d}"
    timestamp = utc_text(at)
    connection.execute("INSERT INTO assignment_events VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (event_id, ticket_id, sequence, "TRANSFERRED", ticket["assigned_agent_id"], to_agent_id, ticket["queue_id"],
         timestamp, "SUPERVISOR", actor_id, "MANUAL_TRANSFER", json.dumps(decision, sort_keys=True)))
    connection.execute("UPDATE tickets SET assigned_agent_id=?,status='ASSIGNED',version=version+1 WHERE ticket_id=?",
                       (to_agent_id, ticket_id))
    append_ticket_event(connection, ticket_id, "STATUS_CHANGED", ticket["status"], "ASSIGNED", "SUPERVISOR", actor_id, reason, at)
    return event_id


def create_resolution(connection, ticket_id: str, agent_id: str, code: str, summary: str, at: datetime | None = None) -> str:
    attempt = connection.execute("SELECT COALESCE(MAX(attempt_no),0)+1 FROM resolutions WHERE ticket_id=?", (ticket_id,)).fetchone()[0]
    resolution_id = f"RES-{ticket_id}-{attempt:03d}"
    connection.execute("INSERT INTO resolutions VALUES (?,?,?,?,?,?,?,?,?)",
        (resolution_id, ticket_id, attempt, code, summary, agent_id, utc_text(at), None, None))
    change_status(connection, ticket_id, "RESOLVED", "RESOLVED", "AGENT", agent_id, summary,
                  {"ASSIGNED", "IN_PROGRESS", "PENDING_CUSTOMER", "ESCALATED", "REOPENED"}, at)
    return resolution_id


def reopen(connection, ticket_id: str, reason: str, at: datetime | None = None) -> str:
    latest = connection.execute("SELECT resolution_id FROM resolutions WHERE ticket_id=? ORDER BY attempt_no DESC LIMIT 1", (ticket_id,)).fetchone()
    if latest is None:
        raise ValueError("Ticket has no resolution to reopen")
    connection.execute("UPDATE resolutions SET reopened_at=? WHERE resolution_id=?", (utc_text(at), latest["resolution_id"]))
    return change_status(connection, ticket_id, "REOPENED", "REOPENED", "CUSTOMER", None, reason, {"RESOLVED", "CLOSED"}, at)

