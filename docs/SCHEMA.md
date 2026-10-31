# Relational schema

## Design principles

- SQLite foreign keys are enabled on every application connection.
- Business identifiers are immutable text primary keys using documented prefixes.
- Current ticket state is cached on `tickets` for efficient queries but must reconcile with append-only event history.
- Assignment, ticket lifecycle, and SLA events are protected by database triggers from updates and deletes.
- Effective-dated records retain historical skill, queue, policy, and calendar context.
- Derived facts such as capacity and breach status are calculated in services/validators, not stored as random flags.

## Core relationships

- Customer 1:N Ticket
- Channel 1:N Ticket and 1:N Message
- Intent 1:N Ticket; Intent N:1 required Skill and default Queue
- Language 1:N Ticket; Agent N:M Language through `agent_languages`
- Agent N:M Skill through `agent_skills`
- Agent N:M Queue through effective-dated `agent_queues`
- Agent 1:N Shift
- Queue 1:N Ticket
- Ticket 1:N Message, AssignmentEvent, TicketEvent, SLAEvent, and Resolution
- Channel + Priority 1:N effective-dated SLA Policy
- BusinessCalendar 1:N calendar hours, exceptions, channels, and SLA policies

## Lifecycle

Allowed ticket states are `NEW`, `QUEUED`, `ASSIGNED`, `IN_PROGRESS`, `PENDING_CUSTOMER`, `ESCALATED`, `RESOLVED`, `CLOSED`, `REOPENED`, and `CANCELLED`. Transition enforcement and reconciliation belong to the lifecycle service in Phase 4; every transition is appended to `ticket_events`.

## Identifier conventions

| Entity | Format | Example |
|---|---|---|
| Customer | `CUS-` + 6 digits | `CUS-000001` |
| Agent | `AGT-` + 6 digits | `AGT-000012` |
| Ticket | `TKT-YYYY-` + 6 digits | `TKT-2026-000001` |
| Message | `MSG-{ticket id}-` + sequence | `MSG-TKT-2026-000001-001` |
| Assignment event | `ASN-{ticket id}-` + sequence | `ASN-TKT-2026-000001-001` |
| SLA event | `SLA-{ticket id}-` + sequence | `SLA-TKT-2026-000001-001` |

## Delete policy

The schema intentionally defines no cascading deletes. Dataset generation creates fresh databases; production-style workflows retain linked history. Event tables additionally reject direct updates and deletes.

