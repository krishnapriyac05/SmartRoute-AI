# SmartRoute AI

SmartRoute AI is an explainable omnichannel support-routing and SLA-management system for the YottaFlex AI 72-hour code challenge.

## Current status

The core implementation is complete through full-scale data verification: relational schema, deterministic generation, routing/SLA/lifecycle services, five controlled anomalies with independent validation, FastAPI, and a live React dashboard. The full profile has been generated and verified at 30,000 tickets, 100 agents, 100,000 messages, and 90 days.

## Requirements

- Python 3.11 or newer
- Node.js 20 or newer

Install the backend and frontend dependencies before starting the application.

## Quick start

From the repository root:

```powershell
python -m backend.scripts.init_db
python -m unittest discover -s backend/tests -v
python -m backend.generator.generate --profile starter --force
python -m backend.generator.reproducibility --profile starter
cd frontend
npm install
cd ..
```

Start the API and frontend in separate terminals:

```powershell
python -m pip install -r backend/requirements.txt
python -m uvicorn backend.app.main:app --reload --port 8000
cd frontend
npm run dev
```

API documentation is available at `http://127.0.0.1:8000/docs`; the frontend defaults to `http://127.0.0.1:5173`.

The first command creates `backend/data/smartroute.db`. It refuses to overwrite an existing database unless `--force` is supplied.

To choose another location:

```powershell
python -m backend.scripts.init_db --database data/starter/smartroute.db
```

## Project layout

- `backend/app/` – SQLite data access, FastAPI endpoints, and business services
- `backend/schema.sql` – authoritative SQLite schema
- `backend/scripts/` – command-line utilities
- `backend/tests/` – executable verification
- `data/` – starter, full, and anomaly ground-truth outputs
- `docs/` – schema, data dictionary, workflow, assumptions, and AI disclosure
- `frontend/` – React/Vite operational dashboard
- `prompts/` – chronological AI prompt history

## Planned phases

1. Foundation and auditable documentation — complete
2. Relational schema and data dictionary — complete
3. Deterministic starter/full data generator — complete
4. Routing, SLA, and lifecycle services — complete
5. Five controlled anomaly scenarios and independent validators — complete
6. FastAPI endpoints — complete
7. React dashboard connected to real API data — complete
8. Full-scale generation and reproducibility proof — complete

See [docs/REQUIREMENTS_CHECKLIST.md](docs/REQUIREMENTS_CHECKLIST.md) for detailed progress and [docs/SCHEMA.md](docs/SCHEMA.md) for relationships.

Before submission, follow [docs/E2E_TESTING_WORKFLOW.md](docs/E2E_TESTING_WORKFLOW.md) and record the actual manual results. The application uses the challenge's SQLite architecture; no hosted database or cloud deployment is required.


