from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from backend.app.database import connect
from backend.app.services.routing import evaluate_agents, retry_waiting_tickets
from backend.generator.generate import DEFAULT_SEED, generate


class WaitingQueueTests(unittest.TestCase):
    def test_waiting_ticket_is_assigned_after_capacity_becomes_available(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            database = root / "waiting.db"
            generate("starter", database, root / "exports", DEFAULT_SEED)
            connection = connect(database)
            try:
                row = connection.execute("""SELECT t.ticket_id,t.created_at,t.language_id,t.queue_id,
                        t.assigned_agent_id,i.required_skill_id
                    FROM tickets t JOIN intents i ON i.intent_id=t.intent_id
                    WHERE t.assigned_agent_id IN (
                        SELECT assigned_agent_id FROM tickets WHERE status IN
                        ('ASSIGNED','IN_PROGRESS','PENDING_CUSTOMER','ESCALATED','REOPENED')
                        GROUP BY assigned_agent_id HAVING COUNT(*)>=2)
                    ORDER BY t.ticket_id LIMIT 1""").fetchone()
                self.assertIsNotNone(row, "Starter data must contain an agent with at least two active tickets")
                at = datetime.fromisoformat(row["created_at"].replace("Z", "+00:00"))
                start = (at - timedelta(hours=1)).isoformat().replace("+00:00", "Z")
                end = (at + timedelta(hours=1)).isoformat().replace("+00:00", "Z")
                effective = (at - timedelta(days=1)).isoformat().replace("+00:00", "Z")
                connection.execute("INSERT OR IGNORE INTO agent_skills VALUES (?,?,?,?,NULL)",
                                   (row["assigned_agent_id"], row["required_skill_id"], 5, effective))
                connection.execute("INSERT OR IGNORE INTO agent_languages VALUES (?,?,?)",
                                   (row["assigned_agent_id"], row["language_id"], "FLUENT"))
                connection.execute("INSERT OR IGNORE INTO agent_queues VALUES (?,?,?,NULL)",
                                   (row["assigned_agent_id"], row["queue_id"], effective))
                connection.execute("INSERT INTO agent_shifts VALUES (?,?,?,?,?)",
                                   ("SHF-WAITING-TEST", row["assigned_agent_id"], start, end, "SCHEDULED"))
                candidate = next(item for item in evaluate_agents(connection, row["ticket_id"], at)
                                 if item["agentId"] == row["assigned_agent_id"])

                connection.execute("UPDATE agents SET status='OFFLINE'")
                connection.execute("UPDATE agents SET status='AVAILABLE',concurrency_limit=? WHERE agent_id=?",
                                   (candidate["activeTickets"] - 1, candidate["agentId"]))
                connection.execute("UPDATE tickets SET assigned_agent_id=NULL,status='QUEUED' WHERE ticket_id=?",
                                   (row["ticket_id"],))

                self.assertEqual(retry_waiting_tickets(connection, at), [])
                queued = connection.execute("SELECT status,assigned_agent_id FROM tickets WHERE ticket_id=?",
                                            (row["ticket_id"],)).fetchone()
                self.assertEqual(queued["status"], "QUEUED")
                self.assertIsNone(queued["assigned_agent_id"])

                connection.execute("UPDATE agents SET concurrency_limit=concurrency_limit+1 WHERE agent_id=?",
                                   (candidate["agentId"],))
                assignments = retry_waiting_tickets(connection, at)
                self.assertEqual(len(assignments), 1)
                self.assertEqual(assignments[0]["ticketId"], row["ticket_id"])
                self.assertEqual(assignments[0]["agentId"], candidate["agentId"])
                assigned = connection.execute("SELECT status,assigned_agent_id FROM tickets WHERE ticket_id=?",
                                              (row["ticket_id"],)).fetchone()
                self.assertEqual(assigned["status"], "ASSIGNED")
                self.assertEqual(assigned["assigned_agent_id"], candidate["agentId"])
                event = connection.execute("""SELECT reason_code FROM assignment_events
                    WHERE ticket_id=? ORDER BY sequence_no DESC LIMIT 1""", (row["ticket_id"],)).fetchone()
                self.assertEqual(event["reason_code"], "WAITING_QUEUE_RETRY")
            finally:
                connection.close()


if __name__ == "__main__":
    unittest.main()
