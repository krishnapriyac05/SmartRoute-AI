# Source and export manifest

## Deterministic configuration

- Generator seed: `20261022`
- Fixed UTC anchor: `2026-08-01T00:00:00Z`
- Coverage: 90 days
- Generator: `backend/generator/generate.py`
- Authoritative schema: `backend/schema.sql`

## Verified full-profile output

| Entity/artifact | Verified value |
|---|---:|
| Tickets | 30,000 |
| Agents | 100 |
| Messages | 100,000 |
| Customers | 10,000 |
| Assignment events | 30,000 |
| Ticket events | 89,550 |
| SLA events | 59,550 |
| Resolutions | 29,550 |
| Agent shifts | 9,000 |
| Export files including manifest | 50 |
| Total generated export size | 226.81 MB |

Every operational table is exported as CSV and JSON. `dataset.sql` provides a restorable SQL representation. `manifest.json` contains row counts and SHA-256 hashes for 49 data artifacts.

The full generated directory is ignored by Git because it is reproducible and large. Reviewers can recreate it with:

```powershell
python -m backend.generator.generate --profile full --force
python -m backend.scripts.validate --database data/full/smartroute.db
python -m backend.generator.reproducibility --profile full
```

## Verification outcome

- Full validation: passed
- Mandatory-anomaly findings in clean full dataset: 0
- Foreign-key violations: 0
- Two-run checksum comparison: passed

