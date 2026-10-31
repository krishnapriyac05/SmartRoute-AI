"""FastAPI application exposing SmartRoute AI operational data."""

from __future__ import annotations

import os
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Iterator

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.app.database import PROJECT_ROOT, connect
from backend.app.services.lifecycle import change_status, create_resolution, reopen, transfer
from backend.app.services.routing import evaluate_agents, require_eligible_agent
from backend.app.services.validation import validate

ACTIVE_STATUSES = ("NEW", "QUEUED", "ASSIGNED", "IN_PROGRESS", "PENDING_CUSTOMER", "ESCALATED", "REOPENED")
DEFAULT_API_DATABASE = PROJECT_ROOT / "data" / "starter" / "smartroute.db"


class TransferRequest(BaseModel):
    to_agent_id: str = Field(alias="toAgentId")
    actor_id: str = Field(alias="actorId")
    reason: str = Field(min_length=3, max_length=500)
    effective_at: datetime | None = Field(default=None, alias="effectiveAt")


class EscalateRequest(BaseModel):
    actor_id: str = Field(alias="actorId")
    reason: str = Field(min_length=3, max_length=500)


class ResolveRequest(BaseModel):
    agent_id: str = Field(alias="agentId")
    resolution_code: str = Field(alias="resolutionCode", min_length=2, max_length=50)
    summary: str = Field(min_length=3, max_length=1000)


class ReopenRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=500)


class CreateTicketRequest(BaseModel):
    customer_id: str = Field(alias="customerId")
    channel_id: str = Field(alias="channelId")
    intent_id: str = Field(alias="intentId")
    language_id: str = Field(alias="languageId")
    subject: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=3, max_length=4000)


class UpdateTicketRequest(BaseModel):
    subject: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=3, max_length=4000)
    priority: str = Field(pattern="^(LOW|MEDIUM|HIGH|CRITICAL)$")
    version: int = Field(ge=1)


def display_channel(code: str) -> str:
    return {"EMAIL": "Email", "CHAT": "Live Chat", "PHONE": "Phone"}.get(code, code.title())


def display_due(due_at: str, status: str, reference: datetime) -> str:
    if status in {"RESOLVED", "CLOSED"}:
        return "Met"
    due = datetime.fromisoformat(due_at.replace("Z", "+00:00"))
    seconds = int((due - reference).total_seconds())
    if seconds <= 0:
        return "Overdue"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes} min"
    return f"{minutes // 60}h {minutes % 60:02d}m"


def create_app(database: str | Path | None = None) -> FastAPI:
    database_path = Path(database or os.getenv("SMARTROUTE_DATABASE", DEFAULT_API_DATABASE)).resolve()
    app = FastAPI(
        title="SmartRoute AI API",
        version="0.4.0",
        description="Explainable support routing, SLA, lifecycle and analytics API.",
    )
    app.state.database = database_path
    origins = os.getenv("SMARTROUTE_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
    app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True,
                       allow_methods=["*"], allow_headers=["*"])

    @contextmanager
    def database_connection() -> Iterator:
        if not app.state.database.exists():
            raise HTTPException(status_code=503, detail="Dataset not found. Generate the starter profile first.")
        connection = connect(app.state.database)
        try:
            yield connection
        finally:
            connection.close()

    def dataset_reference(connection) -> datetime:
        latest = connection.execute("SELECT MAX(created_at) FROM tickets").fetchone()[0]
        return datetime.fromisoformat(latest.replace("Z", "+00:00")) if latest else datetime.now().astimezone()

    def ticket_projection(row, reference: datetime) -> dict:
        return {
            "id": row["ticket_id"], "subject": row["subject"], "customer": row["customer_name"],
            "channel": display_channel(row["channel_code"]), "priority": row["priority"],
            "status": row["status"], "agent": row["agent_name"] or "Unassigned",
            "due": display_due(row["resolution_due_at"], row["status"], reference),
            "createdAt": row["created_at"], "resolutionDueAt": row["resolution_due_at"],
        }

    ticket_select = """SELECT t.ticket_id,t.subject,t.priority,t.status,t.created_at,t.resolution_due_at,
        c.full_name customer_name,ch.code channel_code,a.full_name agent_name
        FROM tickets t JOIN customers c ON c.customer_id=t.customer_id
        JOIN channels ch ON ch.channel_id=t.channel_id LEFT JOIN agents a ON a.agent_id=t.assigned_agent_id"""

    @app.get("/health", tags=["system"])
    def health() -> dict:
        if not app.state.database.exists():
            return {"status": "degraded", "database": str(app.state.database), "datasetReady": False}
        with database_connection() as connection:
            tickets = connection.execute("SELECT COUNT(*) FROM tickets").fetchone()[0]
            integrity = len(connection.execute("PRAGMA foreign_key_check").fetchall()) == 0
        return {"status": "healthy" if integrity else "degraded", "datasetReady": True,
                "database": str(app.state.database), "tickets": tickets, "foreignKeysValid": integrity}

    @app.get("/api/dashboard", tags=["analytics"])
    def dashboard() -> dict:
        with database_connection() as connection:
            reference = dataset_reference(connection)
            placeholders = ",".join("?" for _ in ACTIVE_STATUSES)
            total = connection.execute("SELECT COUNT(*) FROM tickets").fetchone()[0]
            active = connection.execute(f"SELECT COUNT(*) FROM tickets WHERE status IN ({placeholders})", ACTIVE_STATUSES).fetchone()[0]
            resolved = connection.execute("SELECT COUNT(*) FROM tickets WHERE status IN ('RESOLVED','CLOSED')").fetchone()[0]
            at_risk = connection.execute(f"""SELECT COUNT(*) FROM tickets WHERE status IN ({placeholders})
                AND resolution_due_at <= ?""", (*ACTIVE_STATUSES, (reference.replace(microsecond=0).isoformat().replace("+00:00", "Z")))).fetchone()[0]
            channel_rows = connection.execute("""SELECT ch.code,COUNT(*) value FROM tickets t
                JOIN channels ch ON ch.channel_id=t.channel_id GROUP BY ch.code ORDER BY ch.code""").fetchall()
            trend_rows = connection.execute("""WITH dates AS (SELECT date(created_at) day,COUNT(*) created FROM tickets GROUP BY date(created_at)),
                resolved AS (SELECT date(resolved_at) day,COUNT(*) resolved FROM tickets WHERE resolved_at IS NOT NULL GROUP BY date(resolved_at))
                SELECT dates.day,dates.created,COALESCE(resolved.resolved,0) resolved FROM dates LEFT JOIN resolved USING(day)
                ORDER BY dates.day DESC LIMIT 7""").fetchall()[::-1]
            recent = connection.execute(ticket_select + " ORDER BY t.created_at DESC LIMIT 5").fetchall()
        return {"metrics": {"tickets": total, "active": active, "slaAtRisk": at_risk,
                "resolutionRate": round(resolved * 100 / total, 1) if total else 0},
                "channels": [{"name": display_channel(row["code"]), "value": row["value"]} for row in channel_rows],
                "trend": [{"day": row["day"][5:], "created": row["created"], "resolved": row["resolved"]} for row in trend_rows],
                "tickets": [ticket_projection(row, reference) for row in recent]}

    @app.get("/api/tickets", tags=["tickets"])
    def tickets(search: str | None = None, status: str | None = None, priority: str | None = None,
                limit: int = Query(50, ge=1, le=250), offset: int = Query(0, ge=0)) -> dict:
        clauses, values = [], []
        if search:
            clauses.append("(t.ticket_id LIKE ? OR t.subject LIKE ? OR c.full_name LIKE ?)")
            term = f"%{search}%"; values.extend((term, term, term))
        if status:
            clauses.append("t.status = ?"); values.append(status.upper())
        if priority:
            clauses.append("t.priority = ?"); values.append(priority.upper())
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        with database_connection() as connection:
            reference = dataset_reference(connection)
            total = connection.execute("SELECT COUNT(*) FROM tickets t JOIN customers c ON c.customer_id=t.customer_id" + where, values).fetchone()[0]
            rows = connection.execute(ticket_select + where + " ORDER BY t.created_at DESC LIMIT ? OFFSET ?", (*values, limit, offset)).fetchall()
        return {"items": [ticket_projection(row, reference) for row in rows], "total": total, "limit": limit, "offset": offset}

    @app.get("/api/meta/ticket-form", tags=["tickets"])
    def ticket_form_metadata() -> dict:
        with database_connection() as connection:
            return {
                "customers": [dict(row) for row in connection.execute("SELECT customer_id id,full_name name FROM customers ORDER BY customer_id LIMIT 250")],
                "channels": [dict(row) for row in connection.execute("SELECT channel_id id,display_name name FROM channels WHERE is_active=1 ORDER BY channel_id")],
                "intents": [dict(row) for row in connection.execute("SELECT intent_id id,display_name name FROM intents WHERE is_active=1 ORDER BY intent_id")],
                "languages": [dict(row) for row in connection.execute("SELECT language_id id,display_name name FROM languages WHERE is_active=1 ORDER BY language_id")],
            }

    @app.post("/api/tickets", status_code=201, tags=["tickets"])
    def create_ticket(request: CreateTicketRequest) -> dict:
        from backend.app.services.sla import deadline_from_database
        with database_connection() as connection:
            customer = connection.execute("SELECT 1 FROM customers WHERE customer_id=?", (request.customer_id,)).fetchone()
            channel = connection.execute("SELECT 1 FROM channels WHERE channel_id=? AND is_active=1", (request.channel_id,)).fetchone()
            language = connection.execute("SELECT 1 FROM languages WHERE language_id=? AND is_active=1", (request.language_id,)).fetchone()
            intent = connection.execute("SELECT default_queue_id,safety_critical FROM intents WHERE intent_id=? AND is_active=1", (request.intent_id,)).fetchone()
            if not all((customer, channel, language, intent)):
                raise HTTPException(status_code=422, detail="Invalid customer, channel, intent, or language")
            priority = "CRITICAL" if intent["safety_critical"] else "MEDIUM"
            rule = "PRU-SAFETY" if intent["safety_critical"] else "PRU-DEFAULT"
            reference = dataset_reference(connection)
            year = reference.year
            last = connection.execute("SELECT MAX(CAST(substr(ticket_id,10) AS INTEGER)) FROM tickets WHERE ticket_id LIKE ?", (f"TKT-{year}-%",)).fetchone()[0] or 0
            ticket_id = f"TKT-{year}-{last + 1:06d}"
            created_at = reference.replace(microsecond=0)
            first_due = deadline_from_database(connection, request.channel_id, priority, created_at, "FIRST_RESPONSE")
            resolution_due = deadline_from_database(connection, request.channel_id, priority, created_at, "RESOLUTION")
            policy = connection.execute("""SELECT sla_policy_id FROM sla_policies WHERE channel_id=? AND priority=?
                AND effective_from<=? AND (effective_to IS NULL OR effective_to>?) ORDER BY effective_from DESC LIMIT 1""",
                (request.channel_id, priority, created_at.isoformat(), created_at.isoformat())).fetchone()[0]
            stamp = created_at.isoformat().replace("+00:00", "Z")
            connection.execute("""INSERT INTO tickets VALUES
                (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (ticket_id, request.customer_id, request.channel_id,
                request.intent_id, request.language_id, rule, intent["default_queue_id"], None, policy,
                request.subject, request.description, priority, "QUEUED", stamp,
                first_due.isoformat().replace("+00:00", "Z"), resolution_due.isoformat().replace("+00:00", "Z"),
                None, None, None, 1))
            connection.execute("INSERT INTO ticket_events VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (f"EVT-{ticket_id}-001", ticket_id, 1, "CREATED", None, "NEW", stamp, "SYSTEM", None, "Ticket created from UI", "{}"))
            connection.execute("INSERT INTO ticket_events VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (f"EVT-{ticket_id}-002", ticket_id, 2, "STATUS_CHANGED", "NEW", "QUEUED", stamp, "SYSTEM", None, "Awaiting eligible capacity", "{}"))
            connection.execute("INSERT INTO assignment_events VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (f"ASN-{ticket_id}-001", ticket_id, 1, "ROUTING_FAILED", None, None, intent["default_queue_id"],
                 stamp, "SYSTEM", None, "NO_ELIGIBLE_CAPACITY", '{"source":"ui"}'))
            connection.execute("INSERT INTO sla_events VALUES (?,?,?,?,?,?,?,?,?)",
                (f"SLA-{ticket_id}-001", ticket_id, policy, "STARTED", "RESOLUTION", stamp,
                 resolution_due.isoformat().replace("+00:00", "Z"), 0, "SLA policy applied"))
            connection.commit()
        return {"ticketId": ticket_id, "status": "QUEUED", "priority": priority, "version": 1}

    @app.get("/api/tickets/{ticket_id}", tags=["tickets"])
    def ticket_detail(ticket_id: str) -> dict:
        with database_connection() as connection:
            reference = dataset_reference(connection)
            row = connection.execute(ticket_select + " WHERE t.ticket_id=?", (ticket_id,)).fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail="Ticket not found")
            messages = [dict(item) for item in connection.execute(
                "SELECT message_id,sender_type,sender_id,body,sent_at,is_internal FROM messages WHERE ticket_id=? ORDER BY sequence_no", (ticket_id,))]
            events = [dict(item) for item in connection.execute(
                "SELECT event_type,previous_status,new_status,occurred_at,actor_type,actor_id,reason FROM ticket_events WHERE ticket_id=? ORDER BY sequence_no", (ticket_id,))]
            assignment = connection.execute("""SELECT ae.reason_code,ae.decision_json,q.display_name queue_name
                FROM assignment_events ae JOIN queues q ON q.queue_id=ae.queue_id WHERE ae.ticket_id=? ORDER BY ae.sequence_no DESC LIMIT 1""", (ticket_id,)).fetchone()
            ticket_record = connection.execute("SELECT description,version FROM tickets WHERE ticket_id=?", (ticket_id,)).fetchone()
        return {**ticket_projection(row, reference), "description": ticket_record["description"], "version": ticket_record["version"],
                "messages": messages, "events": events, "routing": dict(assignment) if assignment else None}

    @app.patch("/api/tickets/{ticket_id}", tags=["tickets"])
    def update_ticket(ticket_id: str, request: UpdateTicketRequest) -> dict:
        from backend.app.services.lifecycle import append_ticket_event
        from backend.app.services.sla import deadline_from_database
        with database_connection() as connection:
            ticket = connection.execute("SELECT channel_id,created_at,priority,version FROM tickets WHERE ticket_id=?", (ticket_id,)).fetchone()
            if ticket is None:
                raise HTTPException(status_code=404, detail="Ticket not found")
            if ticket["version"] != request.version:
                raise HTTPException(status_code=409, detail="Ticket was modified; refresh and try again")
            started = datetime.fromisoformat(ticket["created_at"].replace("Z", "+00:00"))
            first_due = deadline_from_database(connection, ticket["channel_id"], request.priority, started, "FIRST_RESPONSE")
            resolution_due = deadline_from_database(connection, ticket["channel_id"], request.priority, started, "RESOLUTION")
            policy = connection.execute("""SELECT sla_policy_id FROM sla_policies WHERE channel_id=? AND priority=?
                AND effective_from<=? AND (effective_to IS NULL OR effective_to>?) ORDER BY effective_from DESC LIMIT 1""",
                (ticket["channel_id"], request.priority, ticket["created_at"], ticket["created_at"])).fetchone()[0]
            changed = connection.execute("""UPDATE tickets SET subject=?,description=?,priority=?,sla_policy_id=?,
                first_response_due_at=?,resolution_due_at=?,version=version+1 WHERE ticket_id=? AND version=?""",
                (request.subject, request.description, request.priority, policy,
                 first_due.isoformat().replace("+00:00", "Z"), resolution_due.isoformat().replace("+00:00", "Z"),
                 ticket_id, request.version)).rowcount
            if changed != 1:
                connection.rollback()
                raise HTTPException(status_code=409, detail="Ticket was modified concurrently")
            append_ticket_event(connection, ticket_id, "COMMENTED", None, None, "SUPERVISOR", "UI-ADMIN",
                                "Ticket fields updated from UI")
            connection.commit()
        return {"ticketId": ticket_id, "version": request.version + 1, "priority": request.priority}

    @app.get("/api/agents", tags=["agents"])
    def agents() -> dict:
        with database_connection() as connection:
            rows = connection.execute(f"""SELECT a.agent_id,a.full_name,a.status,a.concurrency_limit,
                COUNT(t.ticket_id) active_tickets FROM agents a LEFT JOIN tickets t ON t.assigned_agent_id=a.agent_id
                AND t.status IN ({','.join('?' for _ in ACTIVE_STATUSES)}) GROUP BY a.agent_id ORDER BY a.agent_id""", ACTIVE_STATUSES).fetchall()
        return {"items": [{**dict(row), "utilization": round(row["active_tickets"] * 100 / row["concurrency_limit"], 1)} for row in rows]}

    @app.get("/api/routing/decisions", tags=["routing"])
    def routing_decisions(limit: int = Query(50, ge=1, le=250)) -> dict:
        with database_connection() as connection:
            rows = connection.execute("""SELECT ae.assignment_event_id,ae.ticket_id,ae.event_type,ae.to_agent_id,
                a.full_name agent_name,q.display_name queue_name,ae.occurred_at,ae.reason_code,ae.decision_json
                FROM assignment_events ae LEFT JOIN agents a ON a.agent_id=ae.to_agent_id JOIN queues q ON q.queue_id=ae.queue_id
                ORDER BY ae.occurred_at DESC LIMIT ?""", (limit,)).fetchall()
        return {"items": [dict(row) for row in rows]}

    @app.get("/api/tickets/{ticket_id}/routing-candidates", tags=["routing"])
    def routing_candidates(ticket_id: str, effective_at: datetime | None = None) -> dict:
        with database_connection() as connection:
            at = effective_at or dataset_reference(connection)
            try:
                candidates = evaluate_agents(connection, ticket_id, at)
            except ValueError as error:
                raise HTTPException(status_code=404, detail=str(error)) from error
        return {"ticketId": ticket_id, "effectiveAt": at.isoformat(), "items": candidates}

    @app.post("/api/tickets/{ticket_id}/transfer", tags=["workflows"])
    def transfer_ticket(ticket_id: str, request: TransferRequest) -> dict:
        with database_connection() as connection:
            at = request.effective_at or dataset_reference(connection)
            try:
                evidence = require_eligible_agent(connection, ticket_id, request.to_agent_id, at)
                event_id = transfer(connection, ticket_id, request.to_agent_id, request.actor_id,
                                    request.reason, evidence, at)
                connection.commit()
            except ValueError as error:
                connection.rollback()
                raise HTTPException(status_code=409, detail=str(error)) from error
        return {"ticketId": ticket_id, "assignmentEventId": event_id, "status": "ASSIGNED"}

    @app.post("/api/tickets/{ticket_id}/escalate", tags=["workflows"])
    def escalate_ticket(ticket_id: str, request: EscalateRequest) -> dict:
        with database_connection() as connection:
            try:
                event_id = change_status(connection, ticket_id, "ESCALATED", "ESCALATED", "SUPERVISOR",
                                         request.actor_id, request.reason,
                                         {"NEW", "QUEUED", "ASSIGNED", "IN_PROGRESS", "PENDING_CUSTOMER", "REOPENED"})
                connection.commit()
            except ValueError as error:
                connection.rollback()
                raise HTTPException(status_code=409, detail=str(error)) from error
        return {"ticketId": ticket_id, "ticketEventId": event_id, "status": "ESCALATED"}

    @app.post("/api/tickets/{ticket_id}/resolve", tags=["workflows"])
    def resolve_ticket(ticket_id: str, request: ResolveRequest) -> dict:
        with database_connection() as connection:
            ticket = connection.execute("SELECT assigned_agent_id FROM tickets WHERE ticket_id=?", (ticket_id,)).fetchone()
            if ticket is None:
                raise HTTPException(status_code=404, detail="Ticket not found")
            if ticket["assigned_agent_id"] != request.agent_id:
                raise HTTPException(status_code=409, detail="Only the assigned agent can resolve this ticket")
            try:
                resolution_id = create_resolution(connection, ticket_id, request.agent_id,
                                                  request.resolution_code, request.summary)
                connection.commit()
            except ValueError as error:
                connection.rollback()
                raise HTTPException(status_code=409, detail=str(error)) from error
        return {"ticketId": ticket_id, "resolutionId": resolution_id, "status": "RESOLVED"}

    @app.post("/api/tickets/{ticket_id}/reopen", tags=["workflows"])
    def reopen_ticket(ticket_id: str, request: ReopenRequest) -> dict:
        with database_connection() as connection:
            try:
                event_id = reopen(connection, ticket_id, request.reason)
                connection.commit()
            except ValueError as error:
                connection.rollback()
                raise HTTPException(status_code=409, detail=str(error)) from error
        return {"ticketId": ticket_id, "ticketEventId": event_id, "status": "REOPENED"}

    @app.get("/api/sla", tags=["sla"])
    def sla_monitor(limit: int = Query(50, ge=1, le=250)) -> dict:
        with database_connection() as connection:
            reference = dataset_reference(connection).isoformat().replace("+00:00", "Z")
            rows = connection.execute("""SELECT ticket_id,priority,status,first_response_due_at,resolution_due_at,
                CASE WHEN resolution_due_at <= ? AND status NOT IN ('RESOLVED','CLOSED','CANCELLED') THEN 1 ELSE 0 END breached
                FROM tickets ORDER BY breached DESC,resolution_due_at LIMIT ?""", (reference, limit)).fetchall()
        return {"referenceTime": reference, "items": [dict(row) for row in rows]}

    @app.get("/api/audit", tags=["audit"])
    def audit(limit: int = Query(100, ge=1, le=500)) -> dict:
        with database_connection() as connection:
            rows = connection.execute("""SELECT ticket_event_id event_id,ticket_id,event_type,previous_status,new_status,
                occurred_at,actor_type,actor_id,reason FROM ticket_events ORDER BY occurred_at DESC LIMIT ?""", (limit,)).fetchall()
        return {"items": [dict(row) for row in rows]}

    @app.get("/api/validation", tags=["validation"])
    def validation_report() -> dict:
        with database_connection() as connection:
            return validate(connection)

    return app


app = create_app()

