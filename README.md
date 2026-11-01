# SmartRoute AI

SmartRoute AI is an explainable omnichannel support-ticket routing and SLA-management application built for the YottaFlex AI 72-hour code challenge. It combines a FastAPI and SQLite backend with a React/Vite operations dashboard, deterministic synthetic data, auditable routing decisions, calendar-aware SLA calculations, immutable lifecycle history, and independent anomaly validation.

The repository is designed to run locally. It does not require PostgreSQL, Render, Vercel, Docker, or any other hosted service.

## What the application does

- Creates, searches, filters, views, and updates support tickets.
- Routes tickets using queue, skill, language, shift, and concurrency-capacity checks.
- Keeps valid tickets in a priority/SLA-ordered waiting queue when all eligible agents are full and retries them when resolution releases capacity.
- Explains why each agent is eligible or ineligible for an assignment.
- Calculates first-response and resolution deadlines from channel and priority policies, including business calendars and exceptions.
- Preserves transfers, escalations, resolutions, reopenings, assignments, and status changes as append-only history.
- Generates deterministic starter and full-scale datasets from seed `20261022`.
- Injects five labelled negative scenarios into an isolated evaluation dataset and validates them independently.
- Exposes operational dashboards for tickets, agents, routing, SLA, analytics, validation, data generation, and audit history.

## Technology stack

| Layer | Implementation |
|---|---|
| Frontend | React 19, React Router 7, Axios, Recharts, Lucide React, Vite 8 |
| API | FastAPI, Pydantic, Uvicorn |
| Data | SQLite with foreign keys, WAL mode, indexes, constraints, and immutable-event triggers |
| Verification | Python `unittest`, FastAPI test client, ESLint, Vite production build |

## Prerequisites

- Git
- Python 3.11, 3.12, or 3.13
- Node.js 20 or newer and npm

Python 3.14 is not currently recommended: the installed FastAPI/Starlette test-client stack can stall under that runtime and emits an `httpx` deprecation warning. The application was developed and its 24-test suite was verified with the supported toolchain recorded in `docs/WORKFLOW_LOG.md`.

Check the installed tools:

```powershell
git --version
python --version
node --version
npm --version
```

## Fresh local setup

### 1. Clone the repository

```powershell
git clone https://github.com/krishnapriyac05/SmartRoute-AI.git
cd SmartRoute-AI
```

All Python module commands below must be run from the repository root.

### 2. Create and activate a Python virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r backend\requirements.txt
```

If PowerShell blocks activation, use Command Prompt and run `.venv\Scripts\activate.bat`, or invoke `.venv\Scripts\python.exe` directly.

### 3. Install frontend dependencies

```powershell
cd frontend
npm install
cd ..
```

`npm install` uses the committed lock file. Do not run `npm audit fix --force` without reviewing its breaking dependency upgrades.

### 4. Generate the local starter database

```powershell
python -m backend.generator.generate --profile starter --force
python -m backend.scripts.validate --database data\starter\smartroute.db
```

This creates the database used by the API at `data/starter/smartroute.db` and refreshes deterministic CSV, JSON, SQL, and manifest exports under `data/starter/exports/`.

Expected starter volume:

- 250 tickets
- 10 agents
- 800 messages
- 90 days of shifts and events
- zero baseline anomaly findings and foreign-key violations

### 5. Start the backend

Open a terminal at the repository root with the virtual environment active:

```powershell
python -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

Verify:

- Health: `http://127.0.0.1:8000/health`
- Interactive API: `http://127.0.0.1:8000/docs`

The root URL intentionally has no page and may return HTTP 404.

### 6. Start the frontend

Open a second terminal:

```powershell
cd frontend
npm run dev
```

Open `http://127.0.0.1:5173`. The dashboard should display `Data source: Live API`.

## Configuration

Configuration is optional for the default local setup.

| Variable | Used by | Default | Purpose |
|---|---|---|---|
| `SMARTROUTE_DATABASE` | Backend | `data/starter/smartroute.db` | Selects the SQLite database exposed by the API. Relative paths are resolved from the current working directory. |
| `SMARTROUTE_CORS_ORIGINS` | Backend | `http://localhost:5173,http://127.0.0.1:5173` | Comma-separated browser origins allowed to call the API. |
| `VITE_API_BASE_URL` | Frontend | `http://localhost:8000/api` | Overrides the API base URL used by Axios. |

PowerShell backend example:

```powershell
$env:SMARTROUTE_DATABASE = "data\starter\smartroute.db"
$env:SMARTROUTE_CORS_ORIGINS = "http://127.0.0.1:5173"
python -m uvicorn backend.app.main:app --reload --port 8000
```

Frontend override:

```powershell
cd frontend
$env:VITE_API_BASE_URL = "http://127.0.0.1:8000/api"
npm run dev
```

## Database and generated data

`backend/schema.sql` is the authoritative SQLite schema. The generator initializes the schema and populates a selected profile.

| Profile | Location | Purpose |
|---|---|---|
| Starter | `data/starter/smartroute.db` | Local development, API, UI, and routine verification |
| Evaluation | `data/ground_truth/evaluation.db` | Isolated dataset containing the five intentional anomalies |
| Full | `data/full/smartroute.db` | Challenge-scale verification: 30,000 tickets, 100 agents, and 100,000 messages |

Database files and full-profile output are ignored by Git. The committed starter exports allow the dataset contents and checksums to be inspected without committing a mutable SQLite file.

The lower-level command below creates an empty schema at `backend/data/smartroute.db`; it is not the normal API dataset-generation workflow:

```powershell
python -m backend.scripts.init_db
```

## Verification commands

### Backend regression suite

```powershell
python -m unittest discover -s backend/tests -v
```

The suite covers schema integrity, deterministic generation, routing and SLA services, lifecycle behavior, APIs, and anomaly validation. The last verified supported-toolchain run passed 24 tests; see `docs/WORKFLOW_LOG.md` for the recorded evidence.

### Frontend checks

```powershell
cd frontend
npm run lint
npm run build
cd ..
```

### Reproducibility

```powershell
python -m backend.generator.reproducibility --profile starter
```

### Five-anomaly evaluation

```powershell
python -m backend.generator.anomalies --force
python -m backend.scripts.validate --database data\ground_truth\evaluation.db --compare-ground-truth
```

Expected comparison: five expected, five detected, five true positives, and zero false positives or false negatives. The evaluation database itself reports `passed: false` because it intentionally contains invalid scenarios.

### Full-scale generation

This operation creates large ignored artifacts and needs additional time and disk space:

```powershell
python -m backend.generator.generate --profile full --force
python -m backend.scripts.validate --database data\full\smartroute.db
python -m backend.generator.reproducibility --profile full
```

## API and UI modules

The FastAPI application exposes health, dashboard, ticket, ticket-form metadata, agent, routing-candidate, SLA, analytics, validation, audit, and lifecycle endpoints. Use `/docs` for the exact request bodies and response schemas.

The frontend provides these routes:

- Dashboard — live KPIs, channel distribution, trend, and recent tickets
- Tickets — global/local search, priority/status/channel filters, creation, and updates
- Ticket details — messages, routing explanation, SLA information, and lifecycle history
- Agents — capacity and current workload
- Routing — assignment evidence and eligibility reasons
- SLA Monitor — deadlines and breach state
- Analytics — operational charts from live API data
- Data Generator — active dataset health and reproducible commands
- Validation — independent data-quality findings
- Audit Trail — chronological append-only events

For mutation testing, regenerate the starter profile afterward to restore the deterministic baseline.

## Project structure

```text
SmartRoute-AI/
|-- backend/
|   |-- app/                 FastAPI application and routing/SLA/lifecycle services
|   |-- generator/           Deterministic profiles, exports, reproducibility, anomalies
|   |-- scripts/             Database initialization and validation commands
|   |-- tests/               Backend regression suite
|   `-- schema.sql           Authoritative SQLite schema
|-- data/
|   |-- starter/exports/     Committed deterministic starter artifacts
|   |-- ground_truth/        Labels for the five controlled anomalies
|   `-- full/                Ignored full-scale generated output
|-- docs/                    Architecture, schema, requirements, validation, and E2E guides
|-- frontend/                React/Vite dashboard
|-- prompts/                 Project-relevant user prompt history
`-- README.md
```

## Reset and troubleshooting

- **API reports “Dataset not found”:** run the starter generation command from the repository root.
- **Frontend shows an unavailable/retry state:** confirm FastAPI is running on port 8000 and `VITE_API_BASE_URL` ends in `/api`.
- **Port already in use:** stop the existing process or start the service on another port and update the frontend API URL.
- **PowerShell cannot import `backend`:** return to the repository root before running Python module commands.
- **Git reports dubious ownership:** trust only this repository with `git config --global --add safe.directory C:/Users/vinay/OneDrive/Desktop/SmartRoute-AI`.
- **Restore deterministic data after UI/API mutations:** run `python -m backend.generator.generate --profile starter --force`.
- **Python 3.14 API tests stall:** use Python 3.11–3.13 in the virtual environment.

## Documentation

- `docs/E2E_TESTING_WORKFLOW.md` — module-wise local acceptance checklist
- `docs/REQUIREMENTS_CHECKLIST.md` — project requirement coverage
- `docs/SCHEMA.md` and `docs/DATA_DICTIONARY.md` — data model documentation
- `docs/VALIDATION_REPORT.md` — validation design and evidence
- `docs/SOURCE_MANIFEST.md` — generated artifact provenance and checksums
- `docs/ASSUMPTIONS.md` — documented implementation assumptions
- `docs/AI_USAGE.md` and `prompts/prompt_history.md` — AI-use disclosure and relevant user instructions
- `docs/WORKFLOW_LOG.md` — chronological implementation and verification record

## Submission scope

This repository is intended for source-code submission through GitHub. Cloud deployment and PostgreSQL support are deliberately out of scope; the challenge implementation remains fully SQLite-based. Before submitting an updated revision, follow `docs/E2E_TESTING_WORKFLOW.md`, inspect `git status`, and confirm that no secrets, local databases, dependency folders, build output, or full-profile artifacts are staged.
