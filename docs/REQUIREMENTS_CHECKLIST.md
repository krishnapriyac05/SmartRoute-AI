# Requirements checklist

## Complete

- [x] Dedicated project structure and Git-ready ignore rules
- [x] Prompt history, workflow log, and honest AI-use disclosure
- [x] All 13 entities named by the “12 core entities” requirement
- [x] Bridge tables for agent skills, languages, queues, and shifts
- [x] Effective-dated priority rules and SLA policies
- [x] Channel calendars, weekly hours, and exceptions
- [x] Immutable assignment, lifecycle, and SLA history
- [x] Separate anomaly ground-truth and validation-run tables
- [x] Schema initialization command
- [x] Automated schema constraints/integrity tests
- [x] Data dictionary, relationships, lifecycle states, ID formats, units, and assumptions
- [x] Fixed-seed starter/full generator profiles
- [x] Required full-profile volumes: 30,000 tickets, 100 agents, 100,000 messages, 90 days
- [x] Stable CSV export manifest with SHA-256 checksums
- [x] Two-run starter checksum reproducibility verification
- [x] Baseline assignment skill/language integrity checks
- [x] React dashboard application shell and responsive navigation
- [x] Dashboard KPI cards, Recharts activity/channel visualizations, and ticket table
- [x] Ticket search and ticket-detail route
- [x] Routed screens for agents, routing, SLA, analytics, generator, validation, and audit
- [x] Central Axios API client with clearly labelled starter-data fallback
- [x] Frontend lint and production build verification
- [x] FastAPI health, dashboard, ticket list/detail, agent, routing, SLA, and audit endpoints
- [x] CORS configuration for local Vite development
- [x] API tests against a freshly generated deterministic database
- [x] Live dashboard metrics and ticket conversations connected end-to-end
- [x] Explainable routing eligibility across availability, capacity, skill, language, queue, and shift
- [x] Validated transfer, escalation, resolution, and reopening API operations
- [x] Optimistic ticket-version checks and append-only lifecycle evidence
- [x] Calendar-aware SLA arithmetic for business hours, after-hours, weekends, and 24×7 channels
- [x] Cross-platform IANA timezone data dependency
- [x] Five isolated mandatory anomaly injectors in a separate evaluation database
- [x] Independent capacity, SLA-calendar, reopen-history, transfer-loop, and safety-priority validators
- [x] Separate CSV and JSON ground-truth exports
- [x] Verified comparison: 5 true positives, 0 false negatives, 0 false positives
- [x] Validation API endpoint and reproducible CLI report
- [x] Live Agent Management screen with capacity/utilization
- [x] Live Routing Decisions screen with assignment evidence
- [x] Live SLA Monitor with breached/on-track results
- [x] Live Analytics, Data Generator status, Validation, and Audit Trail screens
- [x] Shared frontend API loading, error, and retry states
- [x] Stable per-table CSV and JSON exports
- [x] Restorable SQL dataset export
- [x] Full-profile generation with 30,000 tickets, 100 agents, and 100,000 messages
- [x] Full-profile clean validation with zero findings/foreign-key violations
- [x] Full-profile two-run checksum reproducibility proof
- [x] Module-wise end-to-end manual testing workflow and approval gate
- [x] UI ticket creation with database-backed customer, channel, intent, and language fields
- [x] UI ticket subject, description, and priority updates with optimistic version checks
- [x] Ticket priority, status, and channel filters plus local and global ticket search

## Next phases

- [x] JSON and SQL dataset export
- [x] Explainable routing using intent, skill, language, shift, capacity, and queue
- [x] Calendar-aware first-response and resolution SLA calculations
- [x] Lifecycle commands for transfer, escalation, resolve, and reopen
- [ ] Close/cancel lifecycle commands and frontend workflow controls
- [x] Five controlled negative scenarios and independent detection
- [x] FastAPI read endpoints and API tests
- [x] Live FastAPI data on dashboard, tickets, agents, routing, SLA, analytics, generator status, validation, and audit screens
- [x] Two-run checksum reproducibility proof
- [x] Full-scale validation report
- [x] GitHub source publication
- [x] Cloud deployment explicitly excluded from the final submission scope

## Environment note

- The React/Vite frontend is implemented and connected to the live FastAPI API. Frontend lint and production builds were verified during implementation; current verification commands are documented in the root README and E2E workflow.

