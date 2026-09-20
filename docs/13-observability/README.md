# 13 Observability

Written 20 Sep 2026 (US-077), after the debrief decks were reviewed and observability was named as the one production-readiness story the repository did not tell. The layer is built, tested, running locally and on Railway; this folder is its description and its evidence.

| Document | What it holds |
|----------|---------------|
| `OBSERVABILITY.md` | The three telemetry layers (logs, traces, metrics), the metrics endpoint and its token, every metric family with its labels and where it is incremented, the Grafana dashboard row by row, the six alert rules and the objective they encode, the local Compose profile, the two Railway services and their variables, the security controls (T23), what is still missing |
| `grafana-dashboard.png`, `grafana-checks.png`, `grafana-cost-queue.png` | The dashboard as rendered on 20 Sep from a local run with the live model: header and API health; document checks; cost and queue |

The code and configuration: `backend/app/core/metrics.py`, `backend/app/api/v1/metrics.py`, `backend/app/services/metrics.py`, `docker/observability/` (Prometheus templates and start script, alert rules, Grafana provisioning, the dashboard generator). Operator notes: `../09-operations/OPERATIONS.md`, Observability. The threat: `../06-security/THREAT_MODEL.md`, T23. The tests: `backend/tests/integration/test_metrics.py`.
