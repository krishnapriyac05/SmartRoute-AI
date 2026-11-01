# SmartRoute AI – Workflow log

## Entry 001

- Date: 2026-10-31 (Asia/Calcutta)
- Phase: 1 — foundation
- Objective: Inspect the empty workspace, verify tools, and create an auditable project foundation.
- Prompt reference: Prompt 001
- Actual observations: workspace was empty; Python 3.14.6, Node.js 24.18.0, and Git 2.47.0 were available. npm failed because its global `npm-cli.js` was missing. The directory was not yet a Git repository.
- Files changed: repository documentation, ignore rules, project directories.
- Remaining work: repair npm before frontend dependency installation/build.

## Entry 002

- Date: 2026-10-31 (Asia/Calcutta)
- Phase: 2 — relational schema and data dictionary
- Objective: Implement and test the challenge entities, relationships, constraints, effective dates, SLA calendars, and append-only history.
- Prompt reference: Prompt 001
- Implementation: `backend/schema.sql`, connection/initialization helper, CLI, schema tests, schema/data-dictionary/assumption documentation.
- First verification: all five test bodies completed, but teardown failed on Windows because the schema-initialization connection remained open and locked each temporary database. The connection lifecycle was corrected with an explicit `finally: close()` and tests were rerun.
- Final verification command: `python -m unittest discover -s backend/tests -v`
- Final verification result: 5 tests passed in 0.491 seconds. Required tables exist, foreign keys are enabled and valid, agent ID constraints are enforced, history-protection triggers exist, and initialization is idempotent.
- Database initialization result: `backend/data/smartroute.db` created successfully (ignored by Git).
- Git note: repository initialization succeeded. The isolated Codex account required a command-local safe-directory setting to inspect the repository owned by the user's Windows account.
- Remaining work: deterministic generator and business services.

## Entry 003

- Date: 2026-10-31 (Asia/Calcutta)
- Phase: 3 — deterministic data generator
- Objective: Generate starter/full datasets with a fixed seed, stable exports, integrity validation, and reproducibility proof.
- Prompt reference: Prompt 002
- Implementation: generator profiles, deterministic master/transaction/event records, stable CSV exports, SHA-256 manifest, and two-run comparison utility.
- Initial defects found: SQL insertion shape mismatches were caught and corrected. A routing audit then found skill and language mismatches in the first reproducible baseline; eligibility was corrected and regression assertions were added.
- Final verification: `python -m unittest discover -s backend/tests -v` passed 8/8 tests in 1.222 seconds.
- Starter generation: 250 tickets, 10 agents, 800 messages, 100 customers, 900 shift records, 250 assignments, and 418 SLA events using seed `20261022`.
- Reproducibility: two independently generated starter datasets produced identical per-file SHA-256 manifests and row counts.
- Baseline integrity: zero foreign-key, safety-priority, skill-assignment, or language-assignment mismatches.
- Remaining work: calendar-aware SLA service, live routing/capacity service, lifecycle commands, anomalies, API, and frontend integration.

## Entry 004

- Date: 2026-10-31 (Asia/Calcutta)
- Phase: 4 — React dashboard foundation
- Objective: Replace the Vite starter page with the complete SmartRoute AI frontend architecture while preserving backend work.
- Prompt reference: Prompt 003
- Packages installed: `react-router-dom`, `axios`, `recharts`, and `lucide-react` (69 packages added).
- Implementation: responsive application shell, grouped sidebar, top navigation, dashboard metrics and charts, searchable ticket management, ticket detail route, and routed workspaces for all specified screens.
- Data behavior: the shared Axios client requests `VITE_API_BASE_URL` and falls back to a visibly labelled snapshot of the verified starter dataset while FastAPI endpoints remain incomplete.
- Verification: `npm run lint` passed with no errors. `npm run build` passed using Vite 8.3.5; 2,706 modules transformed. Browser rendering was visually inspected at `http://127.0.0.1:5173/` and the dashboard layout, charts, table, and navigation rendered successfully.
- Build note: Vite reported a non-blocking JavaScript chunk-size warning (713.32 kB, 217.84 kB gzip). Route-level code splitting is an optimization for a later phase.
- Dependency note: npm reported six moderate vulnerabilities. No automatic force-upgrade was applied because it could introduce breaking changes; review with `npm audit` before deployment.
- Remaining work: implement FastAPI endpoints and replace fallback data with live database responses, then complete operational workflows.

## Entry 005

- Date: 2026-10-31 (Asia/Calcutta)
- Phase: 5 — FastAPI read API and live frontend integration
- Objective: Expose the generated SQLite dataset through tested endpoints and connect the primary React workflows.
- Prompt reference: Prompt 004
- Dependencies: FastAPI, Uvicorn, and HTTPX added to `backend/requirements.txt` and installed.
- Implementation: health, dashboard analytics, filtered/paginated tickets, ticket details with messages/history/routing evidence, agent workloads, recent routing decisions, SLA exposure, and audit history. Local Vite CORS origins are configurable.
- Automated verification: `python -m unittest discover -s backend/tests -v` passed 14/14 tests in 2.365 seconds. API tests generate their own fixed-seed database and verify reconciliation, filtering, 404 behavior, detail history, health, and operational endpoints.
- Frontend verification: lint and production build passed. With Uvicorn and Vite running together, browser inspection showed `Data source: Live API`; a ticket detail route displayed database messages, agent, routing reason, and three audit events.
- Known note: the installed FastAPI test client emits an upstream deprecation warning about the HTTPX compatibility layer; tests execute successfully and no application failure occurs.
- Remaining work: write operations for routing, transfer, escalation, resolution/reopening; calendar-aware SLA service; anomaly injection/independent validation; connect secondary screens to their API endpoints.

## Entry 006

- Date: 2026-10-31 (Asia/Calcutta)
- Phase: 6 — operational routing, lifecycle, and SLA core
- Objective: Implement explainable eligibility, capacity enforcement, append-only workflow mutations, and calendar-aware deadlines.
- Prompt reference: Prompt 005
- Implementation: agent evaluation reports availability, capacity, effective skill, language, effective queue, and scheduled-shift checks; transfer requires full eligibility. Escalation, resolution, and reopening enforce allowed states and append events. Resolution is restricted to the assigned agent. Ticket versions provide optimistic concurrency protection.
- SLA implementation: timezone-aware business-minute addition handles after-hours starts, multi-day targets, weekends, calendar exceptions, and 24×7 elapsed-time policies. The `tzdata` dependency was added after Windows verification showed the system lacked the IANA timezone database.
- API additions: routing candidates plus transfer, escalate, resolve, and reopen operations with validated request bodies and conflict responses.
- Verification: 20/20 backend tests passed in 1.965 seconds. Frontend lint passed and Vite production build passed (2,706 modules, 1.81 seconds).
- Corrected verification mistake: an initial npm check was run from the repository root and correctly reported that no root `package.json` exists; it was rerun from `frontend` and passed.
- Remaining work: five anomaly injectors and independent validators, secondary frontend operational screens, full-scale generation/checksums, JSON/SQL export, and deployment preparation.

## Entry 007

- Date: 2026-10-31 (Asia/Calcutta)
- Phase: 7 — controlled anomalies and independent validation
- Objective: Produce the five mandatory negative scenarios in a separate evaluation dataset and detect them without reading labels.
- Prompt reference: Prompt 006
- Baseline correction: active generated assignments are now capacity-safe, and all generated SLA deadlines are computed from the configured channel calendar. The clean baseline produces zero mandatory-anomaly findings.
- Injection: controlled capacity overrun, calendar-ignored SLA, missing reopen event, four-step transfer loop, and low-priority security incident. Interactions between anomaly scenarios were isolated to avoid duplicate findings.
- Separation: labels are stored in the evaluation database and exported to separate `ground_truth.csv` and `ground_truth.json`; validation functions inspect only operational entities.
- Verified evaluation: expected 5, detected 5, true positives 5, false negatives 0, false positives 0, foreign-key violations 0.
- Automated verification: 23/23 tests passed in 2.713 seconds.
- Artifacts: `docs/VALIDATION_REPORT.md`, `data/ground_truth/ground_truth.csv`, and `data/ground_truth/ground_truth.json`.
- Remaining work: connect secondary frontend screens, JSON/SQL dataset exports, full-scale generation/checksum report, deployment configuration, and final documentation review.

## Entry 008

- Date: 2026-10-31 (Asia/Calcutta)
- Phase: 8 — live operational frontend screens
- Objective: Replace remaining placeholder screens with useful database-backed interfaces.
- Prompt reference: Prompt 007
- Implementation: live agent capacity/utilization table, routing decision evidence cards, SLA breach table, channel analytics, generator/dataset health, validation results, and immutable audit timeline. Shared loading/error/retry behavior was added for API-dependent screens.
- Automated verification: 23/23 backend tests passed. Frontend lint passed. Vite production build passed with 2,708 modules transformed; the existing non-blocking bundle-size warning remains.
- Browser verification: Agent Management displayed 10 live profiles and workload values. Validation displayed clean-dataset PASS, zero findings, zero foreign-key violations, and the documented 5/5 evaluation result.
- Remaining work: JSON and SQL exports, full-scale generation and checksum proof, frontend code splitting, deployment configuration, and final submission documentation.

## Entry 009

- Date: 2026-10-31 (Asia/Calcutta)
- Phase: 9 — full-scale exports, validation, reproducibility, and E2E test plan
- Objective: Complete the final data-engineering proof and define the manual approval gate before deployment.
- Prompt reference: Prompt 008
- Export implementation: every table now has deterministic CSV and JSON exports; `dataset.sql` provides a restorable SQL export; `manifest.json` records row counts and SHA-256 checksums.
- Starter verification: 23/23 tests passed, starter generation passed, and two-run starter reproducibility passed.
- Full generation: 30,000 tickets, 100 agents, 100,000 messages, 10,000 customers, 30,000 assignment events, 59,550 SLA events, 89,550 ticket events, 29,550 resolutions, and 9,000 shifts.
- Full exports: 50 files including the manifest, totaling 226.81 MB; 49 data artifacts have manifest checksums.
- Full validation: passed with zero mandatory-anomaly findings and zero foreign-key violations.
- Full reproducibility: two independent full-profile runs produced identical artifact checksums using seed `20261022`.
- Manual testing guide: `docs/E2E_TESTING_WORKFLOW.md` covers environment, regression, clean/anomaly/full data, API, lifecycle, frontend, failure recovery, evidence, and final approval.
- Deployment gate: deployment preparation is intentionally paused until the user completes/confirms the E2E workflow.

## Entry 010

- Date: 2026-10-31 (Asia/Calcutta)
- Phase: 10 — interactive ticket management
- Objective: Make the visible create, update, filter, local-search, and global-search controls operational end to end.
- Prompt reference: Prompt 009
- Backend: added live ticket-form metadata, ticket creation, and version-checked ticket update endpoints. Creation records ticket, assignment, status, and SLA history; priority updates recalculate calendar-aware deadlines.
- Frontend: added reusable modal/forms, live New Ticket and Update Ticket workflows, priority/status/channel filters, URL-backed ticket search, and working top navigation search.
- Automated verification: 24/24 backend tests passed. Frontend lint and Vite production build passed; the existing non-blocking bundle-size warning remains.
- Browser verification: created TKT-2026-000251, updated its subject/description/priority, observed SLA remaining change from 8h to 4h and audit count from 2 to 3, filtered QUEUED to one result, and used global search to retrieve TKT-2026-000144.
- Cleanup: the starter dataset was regenerated after browser testing so the committed development baseline remains deterministic.

## Entry 011

- Date: 2026-10-31 (Asia/Calcutta)
- Phase: 11 — GitHub submission readiness
- Objective: Preserve the working SQLite challenge architecture and prepare the repository for source submission without cloud deployment.
- Prompt reference: Prompt 010
- Scope correction: the briefly prepared PostgreSQL/Render/Vercel configuration was removed at the user's direction. No ticket, routing, SLA, validation, generator, or frontend functionality was removed.
- Verification: 24/24 backend tests passed, frontend lint passed, the Vite production build passed, and clean starter validation passed with zero findings or foreign-key violations.
- Repository audit at phase completion: 132 source/submission files were eligible for the initial commit. Large full-profile artifacts, local databases, dependencies, and build output were ignored, and no credential-like strings were found. The repository was subsequently published to `https://github.com/krishnapriyac05/SmartRoute-AI.git`.

## Entry 012

- Date: 2026-11-01 (Asia/Calcutta)
- Phase: 12 — documentation and repository cleanup
- Objective: Make the repository understandable and runnable from a fresh clone using only verified, project-specific instructions.
- Prompt reference: Prompt 011
- Documentation: rewrote the root README with architecture, prerequisites, sequential setup, actual SQLite profiles, environment variables, API/UI modules, verification, reset guidance, troubleshooting, and GitHub submission scope. Updated the frontend guide, E2E terminology, requirements status, and project-relevant prompt history.
- Cleanup: removed the unreferenced Vite starter assets `frontend/src/assets/react.svg`, `frontend/src/assets/vite.svg`, and `frontend/src/assets/hero.png`. No runtime, configuration, dataset, or deployment-required file was removed.
- Frontend verification: ESLint passed and the Vite 8.3.5 production build passed after cleanup. The existing non-blocking JavaScript chunk-size warning remains.
- Data verification: `data/starter/smartroute.db` passed validation with zero findings and zero foreign-key violations.
- Backend verification note: the test suite began successfully after directing temporary files into the workspace, but the API test client stalled under the locally installed Python 3.14 runtime and emitted a Starlette/httpx deprecation warning. The README now recommends Python 3.11–3.13; the last supported-toolchain result remains the recorded 24/24 pass from Entry 011.

## Entry 013

- Date: 2026-11-01 (Asia/Calcutta)
- Phase: 13 — capacity-aware waiting queue and local API usability
- Objective: Preserve valid tickets when eligible agents are full, assign available work automatically, and remove confusing local documentation 404 responses.
- Prompt reference: Prompt 012
- Backend: ticket creation now evaluates skill, language, queue, shift, availability, and capacity before selecting the highest-scoring eligible agent. If no eligible capacity exists, the ticket remains `QUEUED` with a `ROUTING_FAILED` waiting-queue event instead of being rejected.
- Retry workflow: resolving or transferring a ticket retries all unassigned queued tickets in priority, SLA-deadline, creation-time, and ticket-ID order. Successful retry assignments append immutable assignment and ticket-status events.
- API usability: `/` and the accidentally encoded `/docs**` URL redirect to `/docs`; `/favicon.ico` returns an empty successful response.
- Frontend: creation now shows a success modal identifying either automatic assignment or Pending Assignment, including the ticket ID, priority, explanatory message, and assigned agent when applicable.
- Verification: 15 non-API backend tests passed, including the isolated full-capacity/released-capacity waiting-queue scenario. Frontend ESLint and the Vite production build passed. Live `/` and encoded `/docs**` requests both returned redirects to `/docs`, and `/health` reported healthy.


