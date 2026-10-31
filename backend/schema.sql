PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS customers (
    customer_id TEXT PRIMARY KEY CHECK (customer_id GLOB 'CUS-[0-9][0-9][0-9][0-9][0-9][0-9]'),
    full_name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE CHECK (email LIKE '%_@_%._%'),
    phone TEXT UNIQUE,
    timezone TEXT NOT NULL,
    preferred_language_id TEXT,
    customer_tier TEXT NOT NULL DEFAULT 'STANDARD' CHECK (customer_tier IN ('STANDARD','PREMIUM','ENTERPRISE')),
    created_at TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    FOREIGN KEY (preferred_language_id) REFERENCES languages(language_id)
);

CREATE TABLE IF NOT EXISTS channels (
    channel_id TEXT PRIMARY KEY,
    code TEXT NOT NULL UNIQUE CHECK (code IN ('EMAIL','CHAT','PHONE')),
    display_name TEXT NOT NULL,
    calendar_id TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    FOREIGN KEY (calendar_id) REFERENCES business_calendars(calendar_id)
);

CREATE TABLE IF NOT EXISTS languages (
    language_id TEXT PRIMARY KEY,
    iso_code TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL UNIQUE,
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1))
);

CREATE TABLE IF NOT EXISTS intents (
    intent_id TEXT PRIMARY KEY,
    code TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    default_queue_id TEXT,
    required_skill_id TEXT,
    safety_critical INTEGER NOT NULL DEFAULT 0 CHECK (safety_critical IN (0,1)),
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    FOREIGN KEY (default_queue_id) REFERENCES queues(queue_id),
    FOREIGN KEY (required_skill_id) REFERENCES skills(skill_id)
);

CREATE TABLE IF NOT EXISTS priority_rules (
    priority_rule_id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    priority TEXT NOT NULL CHECK (priority IN ('LOW','MEDIUM','HIGH','CRITICAL')),
    condition_json TEXT NOT NULL CHECK (json_valid(condition_json)),
    precedence INTEGER NOT NULL CHECK (precedence >= 0),
    effective_from TEXT NOT NULL,
    effective_to TEXT,
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    CHECK (effective_to IS NULL OR effective_to > effective_from)
);

CREATE TABLE IF NOT EXISTS skills (
    skill_id TEXT PRIMARY KEY,
    code TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1))
);

CREATE TABLE IF NOT EXISTS queues (
    queue_id TEXT PRIMARY KEY,
    code TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    required_skill_id TEXT,
    max_wait_minutes INTEGER NOT NULL CHECK (max_wait_minutes > 0),
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    FOREIGN KEY (required_skill_id) REFERENCES skills(skill_id)
);

CREATE TABLE IF NOT EXISTS agents (
    agent_id TEXT PRIMARY KEY CHECK (agent_id GLOB 'AGT-[0-9][0-9][0-9][0-9][0-9][0-9]'),
    full_name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    timezone TEXT NOT NULL,
    concurrency_limit INTEGER NOT NULL CHECK (concurrency_limit BETWEEN 1 AND 20),
    status TEXT NOT NULL CHECK (status IN ('AVAILABLE','BUSY','OFFLINE','ON_LEAVE')),
    hired_at TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1))
);

CREATE TABLE IF NOT EXISTS agent_skills (
    agent_id TEXT NOT NULL,
    skill_id TEXT NOT NULL,
    proficiency INTEGER NOT NULL CHECK (proficiency BETWEEN 1 AND 5),
    effective_from TEXT NOT NULL,
    effective_to TEXT,
    PRIMARY KEY (agent_id, skill_id, effective_from),
    FOREIGN KEY (agent_id) REFERENCES agents(agent_id),
    FOREIGN KEY (skill_id) REFERENCES skills(skill_id),
    CHECK (effective_to IS NULL OR effective_to > effective_from)
);

CREATE TABLE IF NOT EXISTS agent_languages (
    agent_id TEXT NOT NULL,
    language_id TEXT NOT NULL,
    proficiency TEXT NOT NULL CHECK (proficiency IN ('BASIC','CONVERSATIONAL','FLUENT','NATIVE')),
    PRIMARY KEY (agent_id, language_id),
    FOREIGN KEY (agent_id) REFERENCES agents(agent_id),
    FOREIGN KEY (language_id) REFERENCES languages(language_id)
);

CREATE TABLE IF NOT EXISTS agent_queues (
    agent_id TEXT NOT NULL,
    queue_id TEXT NOT NULL,
    effective_from TEXT NOT NULL,
    effective_to TEXT,
    PRIMARY KEY (agent_id, queue_id, effective_from),
    FOREIGN KEY (agent_id) REFERENCES agents(agent_id),
    FOREIGN KEY (queue_id) REFERENCES queues(queue_id),
    CHECK (effective_to IS NULL OR effective_to > effective_from)
);

CREATE TABLE IF NOT EXISTS agent_shifts (
    shift_id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    starts_at TEXT NOT NULL,
    ends_at TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('SCHEDULED','WORKED','ABSENT','CANCELLED')),
    FOREIGN KEY (agent_id) REFERENCES agents(agent_id),
    CHECK (ends_at > starts_at)
);

CREATE TABLE IF NOT EXISTS business_calendars (
    calendar_id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    timezone TEXT NOT NULL,
    is_24x7 INTEGER NOT NULL DEFAULT 0 CHECK (is_24x7 IN (0,1))
);

CREATE TABLE IF NOT EXISTS calendar_hours (
    calendar_id TEXT NOT NULL,
    weekday INTEGER NOT NULL CHECK (weekday BETWEEN 0 AND 6),
    opens_at TEXT NOT NULL,
    closes_at TEXT NOT NULL,
    PRIMARY KEY (calendar_id, weekday, opens_at),
    FOREIGN KEY (calendar_id) REFERENCES business_calendars(calendar_id),
    CHECK (closes_at > opens_at)
);

CREATE TABLE IF NOT EXISTS calendar_exceptions (
    calendar_id TEXT NOT NULL,
    exception_date TEXT NOT NULL,
    is_closed INTEGER NOT NULL CHECK (is_closed IN (0,1)),
    opens_at TEXT,
    closes_at TEXT,
    label TEXT NOT NULL,
    PRIMARY KEY (calendar_id, exception_date),
    FOREIGN KEY (calendar_id) REFERENCES business_calendars(calendar_id),
    CHECK (is_closed = 1 OR (opens_at IS NOT NULL AND closes_at > opens_at))
);

CREATE TABLE IF NOT EXISTS sla_policies (
    sla_policy_id TEXT PRIMARY KEY,
    channel_id TEXT NOT NULL,
    priority TEXT NOT NULL CHECK (priority IN ('LOW','MEDIUM','HIGH','CRITICAL')),
    calendar_id TEXT NOT NULL,
    first_response_minutes INTEGER NOT NULL CHECK (first_response_minutes > 0),
    resolution_minutes INTEGER NOT NULL CHECK (resolution_minutes > 0),
    escalation_threshold_percent INTEGER NOT NULL CHECK (escalation_threshold_percent BETWEEN 1 AND 100),
    effective_from TEXT NOT NULL,
    effective_to TEXT,
    UNIQUE (channel_id, priority, effective_from),
    FOREIGN KEY (channel_id) REFERENCES channels(channel_id),
    FOREIGN KEY (calendar_id) REFERENCES business_calendars(calendar_id),
    CHECK (effective_to IS NULL OR effective_to > effective_from)
);

CREATE TABLE IF NOT EXISTS tickets (
    ticket_id TEXT PRIMARY KEY CHECK (ticket_id GLOB 'TKT-[0-9][0-9][0-9][0-9]-[0-9][0-9][0-9][0-9][0-9][0-9]'),
    customer_id TEXT NOT NULL,
    channel_id TEXT NOT NULL,
    intent_id TEXT NOT NULL,
    language_id TEXT NOT NULL,
    priority_rule_id TEXT,
    queue_id TEXT NOT NULL,
    assigned_agent_id TEXT,
    sla_policy_id TEXT NOT NULL,
    subject TEXT NOT NULL,
    description TEXT NOT NULL,
    priority TEXT NOT NULL CHECK (priority IN ('LOW','MEDIUM','HIGH','CRITICAL')),
    status TEXT NOT NULL CHECK (status IN ('NEW','QUEUED','ASSIGNED','IN_PROGRESS','PENDING_CUSTOMER','ESCALATED','RESOLVED','CLOSED','REOPENED','CANCELLED')),
    created_at TEXT NOT NULL,
    first_response_due_at TEXT NOT NULL,
    resolution_due_at TEXT NOT NULL,
    first_responded_at TEXT,
    resolved_at TEXT,
    closed_at TEXT,
    version INTEGER NOT NULL DEFAULT 1 CHECK (version > 0),
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
    FOREIGN KEY (channel_id) REFERENCES channels(channel_id),
    FOREIGN KEY (intent_id) REFERENCES intents(intent_id),
    FOREIGN KEY (language_id) REFERENCES languages(language_id),
    FOREIGN KEY (priority_rule_id) REFERENCES priority_rules(priority_rule_id),
    FOREIGN KEY (queue_id) REFERENCES queues(queue_id),
    FOREIGN KEY (assigned_agent_id) REFERENCES agents(agent_id),
    FOREIGN KEY (sla_policy_id) REFERENCES sla_policies(sla_policy_id),
    CHECK (resolution_due_at >= first_response_due_at),
    CHECK (resolved_at IS NULL OR resolved_at >= created_at),
    CHECK (closed_at IS NULL OR closed_at >= created_at)
);

CREATE TABLE IF NOT EXISTS messages (
    message_id TEXT PRIMARY KEY,
    ticket_id TEXT NOT NULL,
    sequence_no INTEGER NOT NULL CHECK (sequence_no > 0),
    sender_type TEXT NOT NULL CHECK (sender_type IN ('CUSTOMER','AGENT','SYSTEM')),
    sender_id TEXT,
    channel_id TEXT NOT NULL,
    body TEXT NOT NULL,
    sent_at TEXT NOT NULL,
    is_internal INTEGER NOT NULL DEFAULT 0 CHECK (is_internal IN (0,1)),
    UNIQUE (ticket_id, sequence_no),
    FOREIGN KEY (ticket_id) REFERENCES tickets(ticket_id),
    FOREIGN KEY (channel_id) REFERENCES channels(channel_id)
);

CREATE TABLE IF NOT EXISTS assignment_events (
    assignment_event_id TEXT PRIMARY KEY,
    ticket_id TEXT NOT NULL,
    sequence_no INTEGER NOT NULL CHECK (sequence_no > 0),
    event_type TEXT NOT NULL CHECK (event_type IN ('ASSIGNED','TRANSFERRED','UNASSIGNED','ROUTING_FAILED')),
    from_agent_id TEXT,
    to_agent_id TEXT,
    queue_id TEXT NOT NULL,
    occurred_at TEXT NOT NULL,
    actor_type TEXT NOT NULL CHECK (actor_type IN ('SYSTEM','AGENT','SUPERVISOR')),
    actor_id TEXT,
    reason_code TEXT NOT NULL,
    decision_json TEXT NOT NULL CHECK (json_valid(decision_json)),
    UNIQUE (ticket_id, sequence_no),
    FOREIGN KEY (ticket_id) REFERENCES tickets(ticket_id),
    FOREIGN KEY (from_agent_id) REFERENCES agents(agent_id),
    FOREIGN KEY (to_agent_id) REFERENCES agents(agent_id),
    FOREIGN KEY (queue_id) REFERENCES queues(queue_id),
    CHECK (from_agent_id IS NULL OR to_agent_id IS NULL OR from_agent_id <> to_agent_id)
);

CREATE TABLE IF NOT EXISTS ticket_events (
    ticket_event_id TEXT PRIMARY KEY,
    ticket_id TEXT NOT NULL,
    sequence_no INTEGER NOT NULL CHECK (sequence_no > 0),
    event_type TEXT NOT NULL CHECK (event_type IN ('CREATED','STATUS_CHANGED','ESCALATED','REOPENED','RESOLVED','CLOSED','COMMENTED')),
    previous_status TEXT,
    new_status TEXT,
    occurred_at TEXT NOT NULL,
    actor_type TEXT NOT NULL CHECK (actor_type IN ('SYSTEM','CUSTOMER','AGENT','SUPERVISOR')),
    actor_id TEXT,
    reason TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(metadata_json)),
    UNIQUE (ticket_id, sequence_no),
    FOREIGN KEY (ticket_id) REFERENCES tickets(ticket_id)
);

CREATE TABLE IF NOT EXISTS sla_events (
    sla_event_id TEXT PRIMARY KEY,
    ticket_id TEXT NOT NULL,
    sla_policy_id TEXT NOT NULL,
    event_type TEXT NOT NULL CHECK (event_type IN ('STARTED','PAUSED','RESUMED','THRESHOLD_REACHED','BREACHED','MET','CANCELLED')),
    target_type TEXT NOT NULL CHECK (target_type IN ('FIRST_RESPONSE','RESOLUTION')),
    occurred_at TEXT NOT NULL,
    due_at TEXT NOT NULL,
    business_minutes_elapsed INTEGER NOT NULL DEFAULT 0 CHECK (business_minutes_elapsed >= 0),
    reason TEXT NOT NULL,
    FOREIGN KEY (ticket_id) REFERENCES tickets(ticket_id),
    FOREIGN KEY (sla_policy_id) REFERENCES sla_policies(sla_policy_id)
);

CREATE TABLE IF NOT EXISTS resolutions (
    resolution_id TEXT PRIMARY KEY,
    ticket_id TEXT NOT NULL,
    attempt_no INTEGER NOT NULL CHECK (attempt_no > 0),
    resolution_code TEXT NOT NULL,
    summary TEXT NOT NULL,
    resolved_by_agent_id TEXT NOT NULL,
    resolved_at TEXT NOT NULL,
    reopened_at TEXT,
    customer_satisfaction INTEGER CHECK (customer_satisfaction BETWEEN 1 AND 5),
    UNIQUE (ticket_id, attempt_no),
    FOREIGN KEY (ticket_id) REFERENCES tickets(ticket_id),
    FOREIGN KEY (resolved_by_agent_id) REFERENCES agents(agent_id),
    CHECK (reopened_at IS NULL OR reopened_at > resolved_at)
);

CREATE TABLE IF NOT EXISTS anomaly_ground_truth (
    anomaly_id TEXT PRIMARY KEY,
    anomaly_type TEXT NOT NULL CHECK (anomaly_type IN ('CAPACITY_EXCEEDED','SLA_CALENDAR_IGNORED','REOPEN_HISTORY_LOST','TRANSFER_LOOP','SAFETY_PRIORITY_CONTRADICTION')),
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    injected_at TEXT NOT NULL,
    expected_detection INTEGER NOT NULL DEFAULT 1 CHECK (expected_detection IN (0,1)),
    notes TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS validation_runs (
    validation_run_id TEXT PRIMARY KEY,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    dataset_seed INTEGER NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('RUNNING','PASSED','FAILED')),
    summary_json TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(summary_json))
);

CREATE INDEX IF NOT EXISTS idx_tickets_status_priority ON tickets(status, priority);
CREATE INDEX IF NOT EXISTS idx_tickets_agent ON tickets(assigned_agent_id, status);
CREATE INDEX IF NOT EXISTS idx_tickets_due ON tickets(resolution_due_at);
CREATE INDEX IF NOT EXISTS idx_messages_ticket_time ON messages(ticket_id, sent_at);
CREATE INDEX IF NOT EXISTS idx_assignment_ticket_time ON assignment_events(ticket_id, occurred_at);
CREATE INDEX IF NOT EXISTS idx_ticket_events_ticket_time ON ticket_events(ticket_id, occurred_at);
CREATE INDEX IF NOT EXISTS idx_sla_events_ticket_time ON sla_events(ticket_id, occurred_at);

CREATE TRIGGER IF NOT EXISTS prevent_assignment_event_update
BEFORE UPDATE ON assignment_events BEGIN SELECT RAISE(ABORT, 'assignment events are immutable'); END;
CREATE TRIGGER IF NOT EXISTS prevent_assignment_event_delete
BEFORE DELETE ON assignment_events BEGIN SELECT RAISE(ABORT, 'assignment events are immutable'); END;
CREATE TRIGGER IF NOT EXISTS prevent_ticket_event_update
BEFORE UPDATE ON ticket_events BEGIN SELECT RAISE(ABORT, 'ticket events are immutable'); END;
CREATE TRIGGER IF NOT EXISTS prevent_ticket_event_delete
BEFORE DELETE ON ticket_events BEGIN SELECT RAISE(ABORT, 'ticket events are immutable'); END;
CREATE TRIGGER IF NOT EXISTS prevent_sla_event_update
BEFORE UPDATE ON sla_events BEGIN SELECT RAISE(ABORT, 'SLA events are immutable'); END;
CREATE TRIGGER IF NOT EXISTS prevent_sla_event_delete
BEFORE DELETE ON sla_events BEGIN SELECT RAISE(ABORT, 'SLA events are immutable'); END;

