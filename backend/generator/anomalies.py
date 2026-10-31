"""Inject the five controlled challenge anomalies into a copied dataset."""

from __future__ import annotations

import argparse
import csv
import json
import shutil
from datetime import datetime, timedelta
from pathlib import Path

from backend.app.database import connect
from backend.app.services.sla import deadline_from_database


def inject(source: Path, target: Path, force: bool = False) -> list[dict]:
    source, target = source.resolve(), target.resolve()
    if not source.exists():
        raise FileNotFoundError(f"Source database not found: {source}")
    if target.exists():
        if not force:
            raise FileExistsError(f"Target database exists: {target}")
        target.unlink()
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    connection = connect(target)
    labels: list[dict] = []
    try:
        # 1. Push one agent beyond concurrency capacity using previously resolved tickets.
        agent = connection.execute("SELECT agent_id,concurrency_limit FROM agents ORDER BY agent_id LIMIT 1").fetchone()
        active = connection.execute("""SELECT COUNT(*) FROM tickets WHERE assigned_agent_id=?
            AND status IN ('ASSIGNED','IN_PROGRESS','PENDING_CUSTOMER','ESCALATED','REOPENED')""", (agent["agent_id"],)).fetchone()[0]
        needed = agent["concurrency_limit"] - active + 1
        tickets = connection.execute("SELECT ticket_id FROM tickets WHERE status='RESOLVED' ORDER BY ticket_id LIMIT ?", (needed,)).fetchall()
        if len(tickets) < needed:
            raise ValueError("Not enough resolved tickets to inject capacity anomaly")
        connection.executemany("UPDATE tickets SET assigned_agent_id=?,status='IN_PROGRESS' WHERE ticket_id=?",
                               ((agent["agent_id"], row["ticket_id"]) for row in tickets))
        labels.append({"type": "CAPACITY_EXCEEDED", "entityType": "agent", "entityId": agent["agent_id"]})

        # 2. Replace a business-calendar deadline with naive elapsed minutes.
        sla_ticket = None
        for row in connection.execute("""SELECT t.ticket_id,t.channel_id,t.priority,t.created_at,t.first_response_due_at,sp.resolution_minutes
            FROM tickets t JOIN channels ch ON ch.channel_id=t.channel_id JOIN sla_policies sp ON sp.sla_policy_id=t.sla_policy_id
            WHERE ch.code='EMAIL' ORDER BY t.ticket_id"""):
            started = datetime.fromisoformat(row["created_at"].replace("Z", "+00:00"))
            expected = deadline_from_database(connection, row["channel_id"], row["priority"], started, "RESOLUTION")
            naive = started + timedelta(minutes=row["resolution_minutes"])
            first_due = datetime.fromisoformat(row["first_response_due_at"].replace("Z", "+00:00"))
            if naive < first_due:
                naive = first_due
            if expected != naive:
                sla_ticket = row
                connection.execute("UPDATE tickets SET resolution_due_at=? WHERE ticket_id=?",
                                   (naive.isoformat().replace("+00:00", "Z"), row["ticket_id"]))
                break
        if sla_ticket is None:
            raise ValueError("No calendar-sensitive email ticket found")
        labels.append({"type": "SLA_CALENDAR_IGNORED", "entityType": "ticket", "entityId": sla_ticket["ticket_id"]})

        excluded = {row["ticket_id"] for row in tickets} | {sla_ticket["ticket_id"]}
        placeholders = ",".join("?" for _ in excluded)

        # 3. Mark a resolved ticket reopened without appending its required event.
        reopen_ticket = connection.execute(f"SELECT ticket_id FROM tickets WHERE status='RESOLVED' AND ticket_id NOT IN ({placeholders}) ORDER BY ticket_id LIMIT 1", tuple(excluded)).fetchone()
        connection.execute("UPDATE tickets SET status='REOPENED',assigned_agent_id=NULL WHERE ticket_id=?", (reopen_ticket["ticket_id"],))
        labels.append({"type": "REOPEN_HISTORY_LOST", "entityType": "ticket", "entityId": reopen_ticket["ticket_id"]})
        excluded.add(reopen_ticket["ticket_id"])

        # 4. Append an A↔B↔A↔B transfer loop.
        transfer_ticket = connection.execute("SELECT ticket_id,queue_id,assigned_agent_id,created_at FROM tickets WHERE ticket_id NOT IN ({}) ORDER BY ticket_id LIMIT 1".format(
            ",".join("?" for _ in excluded)), tuple(excluded)).fetchone()
        agent_a = transfer_ticket["assigned_agent_id"]
        agent_b = connection.execute("SELECT agent_id FROM agents WHERE agent_id<>? ORDER BY agent_id LIMIT 1", (agent_a,)).fetchone()[0]
        sequence = connection.execute("SELECT COALESCE(MAX(sequence_no),0) FROM assignment_events WHERE ticket_id=?", (transfer_ticket["ticket_id"],)).fetchone()[0]
        started = datetime.fromisoformat(transfer_ticket["created_at"].replace("Z", "+00:00"))
        pairs = ((agent_a, agent_b), (agent_b, agent_a), (agent_a, agent_b), (agent_b, agent_a))
        for offset, (from_agent, to_agent) in enumerate(pairs, 1):
            current = sequence + offset
            connection.execute("INSERT INTO assignment_events VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", (
                f"ASN-{transfer_ticket['ticket_id']}-{current:03d}", transfer_ticket["ticket_id"], current,
                "TRANSFERRED", from_agent, to_agent, transfer_ticket["queue_id"],
                (started + timedelta(minutes=offset)).isoformat().replace("+00:00", "Z"),
                "SYSTEM", None, "AUTOMATED_REBALANCE", json.dumps({"injectedInput": True})))
        labels.append({"type": "TRANSFER_LOOP", "entityType": "ticket", "entityId": transfer_ticket["ticket_id"]})
        excluded.add(transfer_ticket["ticket_id"])

        # 5. Contradict the mandatory safety priority rule.
        safety = connection.execute("""SELECT t.ticket_id,t.channel_id,t.created_at FROM tickets t JOIN intents i ON i.intent_id=t.intent_id
            WHERE i.safety_critical=1 AND t.ticket_id NOT IN ({}) ORDER BY t.ticket_id LIMIT 1""".format(
            ",".join("?" for _ in excluded)), tuple(excluded)).fetchone()
        safety_started = datetime.fromisoformat(safety["created_at"].replace("Z", "+00:00"))
        low_policy = connection.execute("""SELECT sla_policy_id FROM sla_policies WHERE channel_id=? AND priority='LOW'
            AND effective_from<=? AND (effective_to IS NULL OR effective_to>?) ORDER BY effective_from DESC LIMIT 1""",
            (safety["channel_id"], safety["created_at"], safety["created_at"])).fetchone()[0]
        safety_first = deadline_from_database(connection, safety["channel_id"], "LOW", safety_started, "FIRST_RESPONSE")
        safety_resolution = deadline_from_database(connection, safety["channel_id"], "LOW", safety_started, "RESOLUTION")
        connection.execute("""UPDATE tickets SET priority='LOW',sla_policy_id=?,first_response_due_at=?,resolution_due_at=?
            WHERE ticket_id=?""", (low_policy, safety_first.isoformat().replace("+00:00", "Z"),
            safety_resolution.isoformat().replace("+00:00", "Z"), safety["ticket_id"]))
        labels.append({"type": "SAFETY_PRIORITY_CONTRADICTION", "entityType": "ticket", "entityId": safety["ticket_id"]})

        injected_at = "2026-10-31T12:00:00Z"
        connection.executemany("INSERT INTO anomaly_ground_truth VALUES (?,?,?,?,?,?,?)",
            ((f"ANM-{index:03d}", label["type"], label["entityType"], label["entityId"], injected_at, 1,
              "Controlled evaluation scenario") for index, label in enumerate(labels, 1)))
        connection.commit()
    finally:
        connection.close()
    ground_truth_dir = target.parent
    (ground_truth_dir / "ground_truth.json").write_text(json.dumps(labels, indent=2) + "\n", encoding="utf-8")
    with (ground_truth_dir / "ground_truth.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=("type", "entityType", "entityId"), lineterminator="\n")
        writer.writeheader()
        writer.writerows(labels)
    return labels


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path("data/starter/smartroute.db"))
    parser.add_argument("--target", type=Path, default=Path("data/ground_truth/evaluation.db"))
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    labels = inject(args.source, args.target, args.force)
    print(json.dumps({"database": str(args.target), "injected": labels}, indent=2))


if __name__ == "__main__":
    main()

