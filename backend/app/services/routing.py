"""Explainable agent eligibility and capacity-aware selection."""

from __future__ import annotations

import json
from datetime import datetime

from backend.app.services.lifecycle import append_ticket_event, next_sequence, utc_text

ACTIVE_STATUSES = ("ASSIGNED", "IN_PROGRESS", "PENDING_CUSTOMER", "ESCALATED", "REOPENED")


def evaluate_agents(connection, ticket_id: str, at: datetime) -> list[dict]:
    ticket = connection.execute("""SELECT t.*,i.required_skill_id FROM tickets t
        JOIN intents i ON i.intent_id=t.intent_id WHERE t.ticket_id=?""", (ticket_id,)).fetchone()
    if ticket is None:
        raise ValueError("Ticket not found")
    placeholders = ",".join("?" for _ in ACTIVE_STATUSES)
    agents = connection.execute(f"""SELECT a.*,
        (SELECT COUNT(*) FROM tickets active WHERE active.assigned_agent_id=a.agent_id
         AND active.status IN ({placeholders})) active_count
        FROM agents a WHERE a.is_active=1 ORDER BY a.agent_id""", ACTIVE_STATUSES).fetchall()
    instant = at.isoformat().replace("+00:00", "Z")
    results = []
    for agent in agents:
        checks = {
            "available": agent["status"] in {"AVAILABLE", "BUSY"},
            "capacity": agent["active_count"] < agent["concurrency_limit"],
            "skill": connection.execute("""SELECT 1 FROM agent_skills WHERE agent_id=? AND skill_id=?
                AND effective_from<=? AND (effective_to IS NULL OR effective_to>?)""",
                (agent["agent_id"], ticket["required_skill_id"], instant, instant)).fetchone() is not None,
            "language": connection.execute("SELECT 1 FROM agent_languages WHERE agent_id=? AND language_id=?",
                (agent["agent_id"], ticket["language_id"])).fetchone() is not None,
            "queue": connection.execute("""SELECT 1 FROM agent_queues WHERE agent_id=? AND queue_id=?
                AND effective_from<=? AND (effective_to IS NULL OR effective_to>?)""",
                (agent["agent_id"], ticket["queue_id"], instant, instant)).fetchone() is not None,
            "on_shift": connection.execute("SELECT 1 FROM agent_shifts WHERE agent_id=? AND starts_at<=? AND ends_at>? AND status='SCHEDULED'",
                (agent["agent_id"], instant, instant)).fetchone() is not None,
        }
        eligible = all(checks.values())
        results.append({"agentId": agent["agent_id"], "agentName": agent["full_name"], "eligible": eligible,
                        "checks": checks, "activeTickets": agent["active_count"], "capacity": agent["concurrency_limit"],
                        "score": (100 - agent["active_count"] * 10) if eligible else 0})
    return sorted(results, key=lambda item: (-item["eligible"], -item["score"], item["agentId"]))


def require_eligible_agent(connection, ticket_id: str, agent_id: str, at: datetime) -> dict:
    result = next((item for item in evaluate_agents(connection, ticket_id, at) if item["agentId"] == agent_id), None)
    if result is None:
        raise ValueError("Agent not found")
    if not result["eligible"]:
        failed = ", ".join(name for name, passed in result["checks"].items() if not passed)
        raise ValueError(f"Agent is not eligible: {failed}")
    return result


def assign_best_eligible_agent(connection, ticket_id: str, at: datetime,
                               reason_code: str = "BEST_ELIGIBLE_AGENT") -> dict | None:
    """Assign the highest-scoring eligible agent, or leave the ticket queued."""
    ticket = connection.execute(
        "SELECT status,queue_id,assigned_agent_id FROM tickets WHERE ticket_id=?", (ticket_id,)
    ).fetchone()
    if ticket is None:
        raise ValueError("Ticket not found")
    if ticket["assigned_agent_id"] is not None:
        return None
    candidate = next((item for item in evaluate_agents(connection, ticket_id, at) if item["eligible"]), None)
    if candidate is None:
        return None

    sequence = next_sequence(connection, "assignment_events", ticket_id)
    event_id = f"ASN-{ticket_id}-{sequence:03d}"
    connection.execute("INSERT INTO assignment_events VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", (
        event_id, ticket_id, sequence, "ASSIGNED", None, candidate["agentId"], ticket["queue_id"],
        utc_text(at), "SYSTEM", None, reason_code, json.dumps(candidate, sort_keys=True)))
    connection.execute(
        "UPDATE tickets SET assigned_agent_id=?,status='ASSIGNED',version=version+1 WHERE ticket_id=?",
        (candidate["agentId"], ticket_id),
    )
    append_ticket_event(connection, ticket_id, "STATUS_CHANGED", ticket["status"], "ASSIGNED",
                        "SYSTEM", None, "Routing completed", at)
    return {"assignmentEventId": event_id, **candidate}


def retry_waiting_tickets(connection, at: datetime) -> list[dict]:
    """Assign waiting tickets in priority, SLA-deadline, then arrival order."""
    waiting = connection.execute("""SELECT ticket_id FROM tickets
        WHERE status='QUEUED' AND assigned_agent_id IS NULL
        ORDER BY CASE priority WHEN 'CRITICAL' THEN 1 WHEN 'HIGH' THEN 2
                 WHEN 'MEDIUM' THEN 3 ELSE 4 END,
                 resolution_due_at, created_at, ticket_id""").fetchall()
    assignments = []
    for row in waiting:
        assigned = assign_best_eligible_agent(connection, row["ticket_id"], at, "WAITING_QUEUE_RETRY")
        if assigned:
            assignments.append({"ticketId": row["ticket_id"], **assigned})
    return assignments

