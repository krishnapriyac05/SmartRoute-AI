from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from backend.app.main import create_app
from backend.generator.generate import DEFAULT_SEED, generate


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory()
        root = Path(cls.temporary.name)
        cls.database = root / "api.db"
        generate("starter", cls.database, root / "exports", DEFAULT_SEED)
        cls.client = TestClient(create_app(cls.database))

    @classmethod
    def tearDownClass(cls) -> None:
        cls.client.close()
        cls.temporary.cleanup()

    def test_health_reports_generated_dataset(self) -> None:
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["tickets"], 250)
        self.assertTrue(response.json()["foreignKeysValid"])

    def test_dashboard_reconciles_to_database(self) -> None:
        data = self.client.get("/api/dashboard").json()
        self.assertEqual(data["metrics"]["tickets"], 250)
        self.assertEqual(sum(item["value"] for item in data["channels"]), 250)
        self.assertEqual(len(data["tickets"]), 5)

    def test_ticket_list_filters_and_paginates(self) -> None:
        response = self.client.get("/api/tickets", params={"priority": "critical", "limit": 10})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertLessEqual(len(data["items"]), 10)
        self.assertTrue(all(item["priority"] == "CRITICAL" for item in data["items"]))

    def test_ticket_detail_includes_history(self) -> None:
        response = self.client.get("/api/tickets/TKT-2026-000001")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertGreater(len(data["messages"]), 0)
        self.assertGreaterEqual(len(data["events"]), 2)
        self.assertIsNotNone(data["routing"])

    def test_missing_ticket_is_404(self) -> None:
        self.assertEqual(self.client.get("/api/tickets/TKT-2026-999999").status_code, 404)

    def test_operational_endpoints_return_items(self) -> None:
        for path in ("/api/agents", "/api/routing/decisions", "/api/sla", "/api/audit"):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200, path)
            self.assertGreater(len(response.json()["items"]), 0, path)

    def test_clean_validation_endpoint_passes(self) -> None:
        response = self.client.get("/api/validation")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["passed"])
        self.assertEqual(response.json()["findingCount"], 0)

    def test_routing_candidates_include_explanations(self) -> None:
        response = self.client.get("/api/tickets/TKT-2026-000001/routing-candidates")
        self.assertEqual(response.status_code, 200)
        candidates = response.json()["items"]
        self.assertEqual(len(candidates), 10)
        self.assertIn("capacity", candidates[0]["checks"])
        self.assertIn("on_shift", candidates[0]["checks"])

    def test_escalate_resolve_and_reopen_preserve_history(self) -> None:
        listing = self.client.get("/api/tickets", params={"status": "assigned", "limit": 1}).json()["items"]
        self.assertTrue(listing)
        ticket = listing[0]
        escalated = self.client.post(f"/api/tickets/{ticket['id']}/escalate",
                                     json={"actorId": "SUP-000001", "reason": "SLA risk review"})
        self.assertEqual(escalated.status_code, 200, escalated.text)
        detail = self.client.get(f"/api/tickets/{ticket['id']}").json()
        decision = self.client.get("/api/routing/decisions", params={"limit": 250}).json()["items"]
        agent_id = next(item["to_agent_id"] for item in decision if item["ticket_id"] == ticket["id"])
        resolved = self.client.post(f"/api/tickets/{ticket['id']}/resolve", json={
            "agentId": agent_id, "resolutionCode": "SOLVED", "summary": "Verified operational resolution"})
        self.assertEqual(resolved.status_code, 200, resolved.text)
        reopened = self.client.post(f"/api/tickets/{ticket['id']}/reopen", json={"reason": "Customer reports recurrence"})
        self.assertEqual(reopened.status_code, 200, reopened.text)
        updated = self.client.get(f"/api/tickets/{ticket['id']}").json()
        self.assertEqual(updated["status"], "REOPENED")
        self.assertGreaterEqual(len(updated["events"]), len(detail["events"]) + 2)

    def test_z_create_and_update_ticket_from_ui_contract(self) -> None:
        meta = self.client.get("/api/meta/ticket-form").json()
        created = self.client.post("/api/tickets", json={
            "customerId": meta["customers"][0]["id"], "channelId": meta["channels"][0]["id"],
            "intentId": meta["intents"][0]["id"], "languageId": meta["languages"][0]["id"],
            "subject": "UI-created test ticket", "description": "Created through the public form contract",
        })
        self.assertEqual(created.status_code, 201, created.text)
        ticket_id = created.json()["ticketId"]
        detail = self.client.get(f"/api/tickets/{ticket_id}").json()
        self.assertEqual(detail["status"], "QUEUED")
        self.assertEqual(detail["version"], 1)
        updated = self.client.patch(f"/api/tickets/{ticket_id}", json={
            "subject": "Updated UI ticket", "description": "Updated through the ticket modal",
            "priority": "HIGH", "version": detail["version"],
        })
        self.assertEqual(updated.status_code, 200, updated.text)
        refreshed = self.client.get(f"/api/tickets/{ticket_id}").json()
        self.assertEqual(refreshed["subject"], "Updated UI ticket")
        self.assertEqual(refreshed["priority"], "HIGH")
        self.assertEqual(refreshed["version"], 2)
        self.assertTrue(any(event["event_type"] == "COMMENTED" for event in refreshed["events"]))


if __name__ == "__main__":
    unittest.main()

