# SmartRoute AI frontend

React/Vite operations interface for SmartRoute AI. The frontend consumes the FastAPI endpoints under `/api`; it does not use mock metrics when the backend is available.

## Run locally

Generate the starter dataset and start FastAPI from the repository root first:

```powershell
python -m backend.generator.generate --profile starter --force
python -m uvicorn backend.app.main:app --reload --port 8000
```

In a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://127.0.0.1:5173`. The default API base is `http://localhost:8000/api`. Override it when necessary:

```powershell
$env:VITE_API_BASE_URL = "http://127.0.0.1:8000/api"
npm run dev
```

## Verification

```powershell
npm run lint
npm run build
```

The interface includes the live dashboard, ticket create/update/search/filter workflows, ticket details, agents, routing evidence, SLA monitoring, analytics, generator health, validation, and audit history. See the root `README.md` and `docs/E2E_TESTING_WORKFLOW.md` for complete setup and acceptance testing.
