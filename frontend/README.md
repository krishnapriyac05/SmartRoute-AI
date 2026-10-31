# SmartRoute AI frontend

React/Vite interface for the SmartRoute AI code-challenge application.

## Run locally

Start FastAPI from the repository root:

```powershell
python -m uvicorn backend.app.main:app --reload --port 8000
```

Then start the frontend:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://127.0.0.1:5173`. The frontend connects to `http://localhost:8000/api` by default.

## Verification

```powershell
npm run lint
npm run build
```

The interface includes the live dashboard, ticket create/update/search/filter workflows, agents, routing evidence, SLA monitoring, analytics, generator health, validation, and audit history.
