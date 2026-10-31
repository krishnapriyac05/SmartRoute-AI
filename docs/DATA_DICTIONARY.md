# Data dictionary

The authoritative field definitions, types, nullability, defaults, checks, unique keys, and foreign keys are executable in `backend/schema.sql`. This document summarizes table purpose and units; keeping constraints in the schema prevents documentation-only validation.

| Table | Purpose | Important rules / units |
|---|---|---|
| `customers` | Synthetic customer profile and preference | Unique email; IANA timezone; optional preferred language |
| `channels` | Email, chat, phone master data | Code enum; one business calendar |
| `tickets` | Current support-case projection | Fixed ID; enum priority/status; ISO-8601 timestamps; due dates derived from policy/calendar |
| `messages` | Ordered conversation content | Unique positive sequence per ticket; immutable ID |
| `intents` | Classification taxonomy | Optional default queue/required skill; safety-critical flag |
| `languages` | Supported-language master | Unique ISO code |
| `priority_rules` | Effective-dated priority decisions | JSON condition; integer precedence; no overlapping selection handled by service |
| `agents` | Support staff and concurrency capacity | Limit measured in simultaneous active tickets, range 1–20 |
| `skills` | Capability master | Unique code |
| `queues` | Routing group | Wait threshold in minutes; optional required skill |
| `assignment_events` | Append-only routing history | Ordered per ticket; JSON decision evidence; update/delete blocked |
| `sla_events` | Append-only SLA history | Business minutes; response/resolution target; update/delete blocked |
| `resolutions` | Resolution attempts | Positive attempt number; optional satisfaction score 1–5; reopening retained |
| `agent_skills` | Effective-dated agent/skill bridge | Proficiency 1–5 |
| `agent_languages` | Agent/language bridge | Basic through native enum |
| `agent_queues` | Effective-dated routing eligibility | Many-to-many bridge |
| `agent_shifts` | Availability windows | ISO-8601 start/end; end after start |
| `business_calendars` | SLA working-time definition | IANA timezone; 24×7 flag |
| `calendar_hours` | Recurring working windows | Weekday 0=Monday through 6=Sunday; local `HH:MM` values |
| `calendar_exceptions` | Holiday/special hours | Local date; closed or explicit opening window |
| `sla_policies` | Effective-dated response/resolution targets | Durations in business minutes; escalation percentage 1–100 |
| `ticket_events` | Append-only lifecycle/audit history | Ordered per ticket; previous/new status and JSON metadata |
| `anomaly_ground_truth` | Labels separate from validator inputs | Exactly five mandatory anomaly types |
| `validation_runs` | Reproducibility/validation metadata | Seed, lifecycle status, JSON summary |

All timestamps are ISO-8601 strings. Generated event timestamps will use UTC (`Z`); calendar calculation converts them using the referenced IANA timezone.

