# SmartRoute AI — Module-wise end-to-end testing workflow

Use this checklist before deployment. Run commands from the repository root unless a step says otherwise. Record actual results in `docs/WORKFLOW_LOG.md`; do not mark a step complete only because the expected result is written here.

## 1. Environment and dependency check

```powershell
python --version
node --version
npm --version
python -m pip install -r backend/requirements.txt
cd frontend
npm install
cd ..
```

Expected: Python 3.11+, Node 20+, and dependency installation without unresolved errors.

## 2. Automated regression suite

```powershell
python -m unittest discover -s backend/tests -v
cd frontend
npm run lint
npm run build
cd ..
```

Pass criteria:

- All backend tests pass.
- ESLint reports no errors.
- Vite creates `frontend/dist`.
- The bundle-size notice is a warning, not a build failure.

## 3. Clean starter dataset module

```powershell
python -m backend.generator.generate --profile starter --force
python -m backend.scripts.validate --database data/starter/smartroute.db
python -m backend.generator.reproducibility --profile starter
```

Confirm:

- 250 tickets, 10 agents, and 800 messages.
- `passed: true`, zero findings, and zero foreign-key violations.
- Reproducibility check passes for seed `20261022`.
- `data/starter/exports` contains CSV and JSON files, `dataset.sql`, and `manifest.json`.

## 4. Negative-scenario and validation module

```powershell
python -m backend.generator.anomalies --force
python -m backend.scripts.validate --database data/ground_truth/evaluation.db --compare-ground-truth
```

Confirm exactly:

- Expected: 5
- Detected: 5
- True positives: 5
- False negatives: 0
- False positives: 0
- Foreign-key violations: 0
- `passed: false` is expected because this database intentionally contains anomalies.

Inspect `data/ground_truth/ground_truth.csv` and confirm labels are separate from operational input tables.

## 5. Full-scale data module

Only run this step when there is sufficient disk space and time.

```powershell
python -m backend.generator.generate --profile full --force
python -m backend.scripts.validate --database data/full/smartroute.db
```

Confirm:

- 30,000 tickets
- 100 agents
- 100,000 messages
- 90 days of shifts/events
- Zero baseline anomaly findings and foreign-key violations
- CSV, JSON, SQL, and manifest artifacts exist under `data/full/exports`

Do not commit the generated full dataset; it is intentionally ignored by Git.

## 6. Backend API module

Terminal 1:

```powershell
python -m uvicorn backend.app.main:app --reload --port 8000
```

Open `http://127.0.0.1:8000/docs` and test:

| Endpoint | Expected check |
|---|---|
| `GET /health` | Healthy, dataset ready, 250 tickets, foreign keys valid |
| `GET /api/dashboard` | Metrics, channel totals, trend, five recent tickets |
| `GET /api/tickets` | Paginated results; test `priority=critical` |
| `GET /api/tickets/{id}` | Messages, events, and routing evidence |
| `GET /api/agents` | 10 agents with workload/capacity |
| `GET /api/tickets/{id}/routing-candidates` | Eligibility checks and reasons |
| `GET /api/sla` | SLA reference time and ticket results |
| `GET /api/validation` | Clean dataset passes with zero findings |
| `GET /api/audit` | Append-only lifecycle events |

The API root `/` may return 404; use `/docs`, `/health`, or `/api/...`.

## 7. Lifecycle and routing workflow module

Use Swagger at `/docs` or another API client. Use a disposable starter database and regenerate it after mutation tests.

1. Select an active ticket using `GET /api/tickets?status=assigned&limit=1`.
2. Inspect its routing candidates.
3. Attempt transfer to an ineligible agent; expect HTTP 409 with failed eligibility checks.
4. Transfer only if an eligible candidate exists; expect an assignment event.
5. Escalate the ticket; expect status `ESCALATED` and a new ticket event.
6. Attempt resolution using the wrong agent; expect HTTP 409.
7. Resolve using the assigned agent; expect a resolution record and `RESOLVED` event.
8. Reopen it; expect status `REOPENED`, preserved earlier resolution, and a new event.
9. Re-read ticket details and audit history to verify no previous event disappeared.

Regenerate the starter database after testing:

```powershell
python -m backend.generator.generate --profile starter --force
```

## 8. Frontend module

Keep Terminal 1 running. Terminal 2:

```powershell
cd frontend
npm run dev
```

Open `http://127.0.0.1:5173` and verify:

- Dashboard says `Data source: Live API`.
- KPI values and channel totals reconcile with the API.
- Tickets search filters visible results.
- Top navigation search sends the query to Tickets and shows the matching ticket(s).
- Filters can be opened and independently restrict priority, status, and channel; Clear restores the unfiltered list.
- New ticket opens a form populated from live customer, channel, intent, and language data. Submitting creates the record and opens its detail page.
- Update ticket changes subject, description, and priority. The detail page refreshes, the audit-event count increases, and a priority change recalculates SLA deadlines.
- Opening a ticket shows real messages, agent, routing reason, and event count.
- Agents shows 10 profiles and utilization.
- Routing shows assignment evidence.
- SLA Monitor shows deadlines and breach status.
- Analytics charts render without console errors.
- Data Generator shows the loaded dataset health.
- Validation shows clean PASS and zero findings.
- Audit Trail shows chronological events.
- Sidebar works on desktop and the menu opens/closes on a narrow/mobile viewport.
- Refreshing a nested URL such as `/tickets/TKT-2026-000001` works in development.

## 9. Failure and recovery module

1. Stop FastAPI while leaving Vite running.
2. Confirm API-dependent screens show a clear unavailable/retry state.
3. Restart FastAPI.
4. Click Retry and confirm live data returns.
5. Request a nonexistent ticket and confirm the API returns HTTP 404.
6. Submit an invalid lifecycle transition and confirm HTTP 409 without partial database changes.

## 10. Evidence and final approval gate

Capture and retain:

- Backend test summary
- Frontend lint/build summary
- Clean validation JSON
- Five-anomaly comparison JSON
- Full-profile row counts and manifest checksums
- Screenshots of Dashboard, Ticket Details, Validation, and Audit Trail
- Any issues found, fixes applied, and retest results

Before deployment, confirm all critical checks below:

- [ ] Automated tests, lint, and build pass
- [ ] Clean starter data passes validation
- [ ] Five anomaly scenarios are detected exactly
- [ ] Full data row counts and exports are verified
- [ ] API endpoints and lifecycle rejection cases work
- [ ] Every frontend route loads live data
- [ ] Error/retry behavior works
- [ ] README and workflow log reflect actual results
- [ ] No secrets or generated full database are staged in Git

Deployment preparation begins only after the user confirms this end-to-end checklist is complete.
