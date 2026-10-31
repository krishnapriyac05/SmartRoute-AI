# Validation report

## Verified run

- Date: 2026-10-31
- Seed: `20261022`
- Starter baseline: 250 tickets, 10 agents, 800 messages
- Baseline mandatory-anomaly findings: **0**
- Evaluation labels: **5**
- Independent detections: **5**
- True positives: **5**
- False negatives: **0**
- False positives: **0**
- Foreign-key violations: **0**

| Scenario | Labelled entity | Evidence detected independently |
|---|---|---|
| Agent beyond capacity | `AGT-000001` | 5 active tickets against limit 4 |
| SLA ignores channel calendar | `TKT-2026-000001` | Stored deadline differs from recomputed business-calendar deadline |
| Reopened ticket loses history | `TKT-2026-000003` | Current status is reopened with no corresponding reopen event |
| Transfer loop | `TKT-2026-000004` | Repeated A→B→A→B assignment cycle |
| Safety priority contradiction | `TKT-2026-000005` | Security incident classified as low rather than critical |

Ground-truth labels are exported separately to `data/ground_truth/ground_truth.csv` and `ground_truth.json`. Validator code does not read those labels; comparison occurs only after detection.

## Reproduce

```powershell
python -m backend.generator.generate --profile starter --force
python -m backend.generator.anomalies --force
python -m backend.scripts.validate --database data/ground_truth/evaluation.db --compare-ground-truth
python -m unittest discover -s backend/tests -v
```
