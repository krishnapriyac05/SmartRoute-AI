# Assumptions

- The challenge wording says “12 core entities” but enumerates Customer, Channel, Ticket, Message, Intent, Language, PriorityRule, Agent, Skill, Queue, AssignmentEvent, SLAEvent, and Resolution (13 names). The schema implements all 13.
- Suggested SLA durations in the supplied analysis are assumptions, not official YottaFlex values. Phase 3 will seed configurable policies rather than hard-code them in routing logic.
- `Asia/Kolkata` is the canonical IANA timezone name; generated data will not use the ambiguous abbreviation `IST`.
- SQLite stores timestamps as validated application-level ISO-8601 text. Cross-field ordering checks are included where SQLite can enforce them safely.
- The event store is append-only. Corrections will be represented by compensating events, never history mutation.
- Full generated files are excluded from Git; a small starter dataset and deterministic generation commands will be committed.

