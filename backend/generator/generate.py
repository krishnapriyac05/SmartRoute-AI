"""Generate deterministic SmartRoute AI datasets and stable CSV exports."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Iterable

from backend.app.database import connect, initialize_database
from backend.app.services.sla import deadline_from_database

DEFAULT_SEED = 20261022
ANCHOR = datetime(2026, 8, 1, tzinfo=UTC)


@dataclass(frozen=True)
class Profile:
    agents: int
    tickets: int
    messages: int
    days: int = 90


PROFILES = {
    "starter": Profile(agents=10, tickets=250, messages=800),
    "full": Profile(agents=100, tickets=30_000, messages=100_000),
}

LANGUAGES = (("LNG-EN", "en", "English"), ("LNG-HI", "hi", "Hindi"),
             ("LNG-TE", "te", "Telugu"), ("LNG-TA", "ta", "Tamil"),
             ("LNG-KN", "kn", "Kannada"))
SKILLS = (("SKL-BILL", "BILLING", "Billing"), ("SKL-TECH", "TECHNICAL", "Technical"),
          ("SKL-ACCT", "ACCOUNT", "Account Management"), ("SKL-SEC", "SECURITY", "Security"),
          ("SKL-REF", "REFUNDS", "Refunds"))
QUEUES = (("QUE-BILL", "BILLING", "Billing", "SKL-BILL"),
          ("QUE-TECH", "TECHNICAL", "Technical Support", "SKL-TECH"),
          ("QUE-ACCT", "ACCOUNT", "Account Support", "SKL-ACCT"),
          ("QUE-SEC", "SECURITY", "Security Response", "SKL-SEC"),
          ("QUE-REF", "REFUNDS", "Refunds", "SKL-REF"))
INTENTS = (("INT-PAY", "PAYMENT_FAILURE", "Payment failure", "QUE-BILL", "SKL-BILL", 0),
           ("INT-BUG", "TECHNICAL_ISSUE", "Technical issue", "QUE-TECH", "SKL-TECH", 0),
           ("INT-LOG", "LOGIN_PROBLEM", "Login problem", "QUE-ACCT", "SKL-ACCT", 0),
           ("INT-SEC", "SECURITY_INCIDENT", "Security incident", "QUE-SEC", "SKL-SEC", 1),
           ("INT-REF", "REFUND_REQUEST", "Refund request", "QUE-REF", "SKL-REF", 0))
PRIORITIES = ("LOW", "MEDIUM", "HIGH", "CRITICAL")
CHANNELS = (("CHN-EMAIL", "EMAIL", "Email", "CAL-BUSINESS"),
            ("CHN-CHAT", "CHAT", "Live Chat", "CAL-24X7"),
            ("CHN-PHONE", "PHONE", "Phone", "CAL-24X7"))


def iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def insert_many(connection, sql: str, rows: Iterable[tuple]) -> None:
    connection.executemany(sql, rows)


def seed_master_data(connection) -> None:
    insert_many(connection, "INSERT INTO business_calendars VALUES (?,?,?,?)", (
        ("CAL-BUSINESS", "India business hours", "Asia/Kolkata", 0),
        ("CAL-24X7", "24 x 7", "Asia/Kolkata", 1),
    ))
    insert_many(connection, "INSERT INTO calendar_hours VALUES (?,?,?,?)",
                (("CAL-BUSINESS", day, "09:00", "18:00") for day in range(5)))
    insert_many(connection, "INSERT INTO languages VALUES (?,?,?,1)", LANGUAGES)
    insert_many(connection, "INSERT INTO skills VALUES (?,?,?,1)", SKILLS)
    insert_many(connection, "INSERT INTO queues VALUES (?,?,?,?,?,1)",
                ((qid, code, name, skill, 30) for qid, code, name, skill in QUEUES))
    insert_many(connection, "INSERT INTO channels VALUES (?,?,?,?,1)", CHANNELS)
    insert_many(connection, "INSERT INTO intents VALUES (?,?,?,?,?,?,1)", INTENTS)
    now = iso(ANCHOR - timedelta(days=365))
    rules = (
        ("PRU-SAFETY", "Safety incidents are critical", "CRITICAL", '{"safety_critical":true}', 100, now, None, 1),
        ("PRU-PREMIUM", "Premium customer priority", "HIGH", '{"customer_tier":"PREMIUM"}', 50, now, None, 1),
        ("PRU-DEFAULT", "Default priority", "MEDIUM", '{}', 0, now, None, 1),
    )
    insert_many(connection, "INSERT INTO priority_rules VALUES (?,?,?,?,?,?,?,?)", rules)
    targets = {"LOW": (480, 1440, 80), "MEDIUM": (240, 480, 75),
               "HIGH": (60, 240, 70), "CRITICAL": (15, 60, 50)}
    policies = []
    for channel_id, _, _, calendar_id in CHANNELS:
        for priority, (response, resolution, threshold) in targets.items():
            policies.append((f"POL-{channel_id[4:]}-{priority}", channel_id, priority, calendar_id,
                             response, resolution, threshold, now, None))
    insert_many(connection, "INSERT INTO sla_policies VALUES (?,?,?,?,?,?,?,?,?)", policies)


def seed_agents(connection, rng: random.Random, profile: Profile) -> list[dict]:
    agents = []
    for number in range(1, profile.agents + 1):
        agent_id = f"AGT-{number:06d}"
        agents.append({"id": agent_id, "limit": 3 + number % 4})
        connection.execute("INSERT INTO agents VALUES (?,?,?,?,?,?,?,?)", (
            agent_id, f"Support Agent {number:03d}", f"agent{number:03d}@smartroute.test",
            "Asia/Kolkata", 3 + number % 4, "AVAILABLE", iso(ANCHOR - timedelta(days=400-number)), 1,
        ))
        primary = (number - 1) % len(SKILLS)
        secondary = (primary + 1 + number % (len(SKILLS) - 1)) % len(SKILLS)
        for index in sorted({primary, secondary}):
            connection.execute("INSERT INTO agent_skills VALUES (?,?,?,?,?)", (
                agent_id, SKILLS[index][0], 3 + (number + index) % 3, iso(ANCHOR - timedelta(days=180)), None))
        # Every generated routing team covers every supported language. Skill
        # specialization still differentiates agents and drives eligibility.
        for index in range(len(LANGUAGES)):
            connection.execute("INSERT INTO agent_languages VALUES (?,?,?)", (
                agent_id, LANGUAGES[index][0], "FLUENT" if index else "NATIVE"))
        for skill_index in sorted({primary, secondary}):
            connection.execute("INSERT INTO agent_queues VALUES (?,?,?,?)", (
                agent_id, QUEUES[skill_index][0], iso(ANCHOR - timedelta(days=180)), None))
        for day in range(profile.days):
            shift_start = ANCHOR + timedelta(days=day, hours=3, minutes=30 + (number % 3) * 30)
            connection.execute("INSERT INTO agent_shifts VALUES (?,?,?,?,?)", (
                f"SHF-{number:06d}-{day+1:03d}", agent_id, iso(shift_start),
                iso(shift_start + timedelta(hours=9)), "SCHEDULED"))
    return agents


def ticket_priority(intent_index: int, tier: str, rng: random.Random) -> tuple[str, str]:
    if INTENTS[intent_index][5]:
        return "CRITICAL", "PRU-SAFETY"
    if tier == "PREMIUM" and rng.random() < 0.55:
        return "HIGH", "PRU-PREMIUM"
    value = rng.random()
    return ("LOW" if value < .2 else "MEDIUM" if value < .78 else "HIGH"), "PRU-DEFAULT"


def generate_records(connection, rng: random.Random, profile: Profile) -> None:
    agents = seed_agents(connection, rng, profile)
    active_counts = {agent["id"]: 0 for agent in agents}
    customer_count = max(100, profile.tickets // 3)
    tiers = ("STANDARD", "STANDARD", "PREMIUM", "ENTERPRISE")
    for number in range(1, customer_count + 1):
        language = LANGUAGES[(number * 7) % len(LANGUAGES)][0]
        connection.execute("INSERT INTO customers VALUES (?,?,?,?,?,?,?,?,?)", (
            f"CUS-{number:06d}", f"Customer {number:06d}", f"customer{number:06d}@example.test",
            f"+91{7000000000+number:010d}", "Asia/Kolkata", language, tiers[number % len(tiers)],
            iso(ANCHOR - timedelta(days=30 + number % 700)), 1))

    message_allocations = [1] * profile.tickets
    for index in range(profile.messages - profile.tickets):
        message_allocations[index % profile.tickets] += 1

    for index in range(profile.tickets):
        number = index + 1
        ticket_id = f"TKT-2026-{number:06d}"
        customer_no = 1 + (index * 7919) % customer_count
        customer_id = f"CUS-{customer_no:06d}"
        tier = tiers[customer_no % len(tiers)]
        intent_index = rng.randrange(len(INTENTS))
        intent = INTENTS[intent_index]
        priority, rule = ticket_priority(intent_index, tier, rng)
        channel = CHANNELS[rng.randrange(len(CHANNELS))]
        language = LANGUAGES[(customer_no * 7) % len(LANGUAGES)][0]
        created = ANCHOR + timedelta(seconds=rng.randrange(profile.days * 86400))
        policy = f"POL-{channel[0][4:]}-{priority}"
        targets = {"LOW": (480, 1440), "MEDIUM": (240, 480), "HIGH": (60, 240), "CRITICAL": (15, 60)}
        response_minutes, resolution_minutes = targets[priority]
        candidates = [agent for pos, agent in enumerate(agents) if pos % len(SKILLS) == intent_index]
        will_resolve = rng.random() < .72
        available = [agent for agent in candidates if active_counts[agent["id"]] < agent["limit"]]
        if not will_resolve and not available:
            will_resolve = True
        candidate_pool = candidates if will_resolve else available
        assigned = min(candidate_pool, key=lambda agent: (active_counts[agent["id"]], agent["id"]))
        if not will_resolve:
            active_counts[assigned["id"]] += 1
        first_due = deadline_from_database(connection, channel[0], priority, created, "FIRST_RESPONSE")
        resolution_due = deadline_from_database(connection, channel[0], priority, created, "RESOLUTION")
        resolved = created + timedelta(minutes=max(response_minutes, int(resolution_minutes * (.25 + rng.random() * .65)))) if will_resolve else None
        status = "RESOLVED" if will_resolve else ("IN_PROGRESS" if rng.random() < .7 else "ASSIGNED")
        connection.execute("""INSERT INTO tickets VALUES
            (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
            ticket_id, customer_id, channel[0], intent[0], language, rule, intent[3], assigned["id"], policy,
            f"{intent[2]} #{number}", f"Customer reported {intent[2].lower()} through {channel[2].lower()}.",
            priority, status, iso(created), iso(first_due),
            iso(resolution_due), iso(created + timedelta(minutes=response_minutes // 2)),
            iso(resolved) if resolved else None, None, 1))
        connection.execute("INSERT INTO ticket_events VALUES (?,?,?,?,?,?,?,?,?,?,?)", (
            f"EVT-{ticket_id}-001", ticket_id, 1, "CREATED", None, "NEW", iso(created),
            "SYSTEM", None, "Ticket received", "{}"))
        connection.execute("INSERT INTO ticket_events VALUES (?,?,?,?,?,?,?,?,?,?,?)", (
            f"EVT-{ticket_id}-002", ticket_id, 2, "STATUS_CHANGED", "NEW", "ASSIGNED",
            iso(created + timedelta(seconds=5)), "SYSTEM", None, "Routing completed", "{}"))
        connection.execute("INSERT INTO assignment_events VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", (
            f"ASN-{ticket_id}-001", ticket_id, 1, "ASSIGNED", None, assigned["id"], intent[3],
            iso(created + timedelta(seconds=5)), "SYSTEM", None, "BEST_ELIGIBLE_AGENT",
            json.dumps({"skill": intent[4], "language": language, "capacity_limit": assigned["limit"]}, sort_keys=True)))
        connection.execute("INSERT INTO sla_events VALUES (?,?,?,?,?,?,?,?,?)", (
            f"SLA-{ticket_id}-001", ticket_id, policy, "STARTED", "RESOLUTION", iso(created),
            iso(resolution_due), 0, "SLA policy applied"))
        if resolved:
            connection.execute("INSERT INTO ticket_events VALUES (?,?,?,?,?,?,?,?,?,?,?)", (
                f"EVT-{ticket_id}-003", ticket_id, 3, "RESOLVED", "ASSIGNED", "RESOLVED",
                iso(resolved), "AGENT", assigned["id"], "Issue resolved", "{}"))
            connection.execute("INSERT INTO resolutions VALUES (?,?,?,?,?,?,?,?,?)", (
                f"RES-{ticket_id}-001", ticket_id, 1, "SOLVED", "Issue resolved after investigation",
                assigned["id"], iso(resolved), None, 3 + number % 3))
            connection.execute("INSERT INTO sla_events VALUES (?,?,?,?,?,?,?,?,?)", (
                f"SLA-{ticket_id}-002", ticket_id, policy,
                "MET" if resolved <= resolution_due else "BREACHED",
                "RESOLUTION", iso(resolved), iso(resolution_due),
                int((resolved-created).total_seconds() // 60), "Resolution recorded"))
        for sequence in range(1, message_allocations[index] + 1):
            sender = "CUSTOMER" if sequence % 2 else "AGENT"
            sender_id = customer_id if sender == "CUSTOMER" else assigned["id"]
            sent = created + timedelta(minutes=sequence * 4)
            connection.execute("INSERT INTO messages VALUES (?,?,?,?,?,?,?,?,?)", (
                f"MSG-{ticket_id}-{sequence:03d}", ticket_id, sequence, sender, sender_id,
                channel[0], f"Synthetic {sender.lower()} message {sequence} for {ticket_id}", iso(sent), 0))


def table_names(connection) -> list[str]:
    return [row[0] for row in connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]


def export_csv(connection, output: Path) -> dict[str, dict]:
    output.mkdir(parents=True, exist_ok=True)
    manifest = {}
    for table in table_names(connection):
        target = output / f"{table}.csv"
        cursor = connection.execute(f'SELECT * FROM "{table}" ORDER BY rowid')
        with target.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle, lineterminator="\n")
            writer.writerow([item[0] for item in cursor.description])
            count = 0
            for row in cursor:
                writer.writerow(row)
                count += 1
        manifest[target.name] = {"rows": count, "sha256": hashlib.sha256(target.read_bytes()).hexdigest()}
    return manifest


def export_json(connection, output: Path) -> dict[str, dict]:
    manifest = {}
    for table in table_names(connection):
        target = output / f"{table}.json"
        cursor = connection.execute(f'SELECT * FROM "{table}" ORDER BY rowid')
        columns = [item[0] for item in cursor.description]
        count = 0
        with target.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write("[\n")
            first = True
            for row in cursor:
                if not first:
                    handle.write(",\n")
                handle.write(json.dumps(dict(zip(columns, row)), ensure_ascii=False, sort_keys=True, separators=(",", ":")))
                first = False
                count += 1
            handle.write("\n]\n")
        manifest[target.name] = {"rows": count, "sha256": hashlib.sha256(target.read_bytes()).hexdigest()}
    return manifest


def export_sql(connection, output: Path) -> dict[str, dict]:
    target = output / "dataset.sql"
    with target.open("w", encoding="utf-8", newline="\n") as handle:
        for line in connection.iterdump():
            handle.write(line + "\n")
    return {target.name: {"rows": None, "sha256": hashlib.sha256(target.read_bytes()).hexdigest()}}


def generate(profile_name: str, database: Path, output: Path, seed: int = DEFAULT_SEED, force: bool = False) -> dict:
    if profile_name not in PROFILES:
        raise ValueError(f"Unknown profile: {profile_name}")
    if database.exists():
        if not force:
            raise FileExistsError(f"Database already exists: {database}")
        database.unlink()
    if output.exists() and force:
        shutil.rmtree(output)
    initialize_database(database)
    rng = random.Random(seed)
    connection = connect(database)
    try:
        seed_master_data(connection)
        generate_records(connection, rng, PROFILES[profile_name])
        connection.commit()
        files = export_csv(connection, output)
        files.update(export_json(connection, output))
        files.update(export_sql(connection, output))
        counts = {table: connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
                  for table in table_names(connection)}
    finally:
        connection.close()
    manifest = {"profile": profile_name, "seed": seed, "anchor_utc": iso(ANCHOR),
                "counts": counts, "files": files}
    manifest_path = output / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=PROFILES, default="starter")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--database", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    database = args.database or Path("data") / args.profile / "smartroute.db"
    output = args.output or Path("data") / args.profile / "exports"
    manifest = generate(args.profile, database, output, args.seed, args.force)
    print(json.dumps({"profile": args.profile, "seed": args.seed, "counts": manifest["counts"]}, indent=2))


if __name__ == "__main__":
    main()

