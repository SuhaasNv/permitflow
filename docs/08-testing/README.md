# 08 Testing

One document: what each layer of tests protects, where it lives and how to run it. Written at the end of Sprint 2 (18 Sep 2026) from what existed and updated as layers were added.

| Document | What it holds |
|----------|---------------|
| `TEST_STRATEGY.md` | Principles (real PostgreSQL, no mocked ORM), the layers (backend unit and integration, frontend unit, Playwright journeys and the accessibility gate, the AI gate, the live evaluation), what each protects, the coverage thresholds, and the commands |

The tests themselves: `backend/tests/` (including `integration/test_metrics.py` for the observability layer), `frontend/src/**/*.test.tsx`, `frontend/e2e/`, `backend/evals/`. CI runs all of it: `.github/workflows/ci.yml` and `ai-gate.yml`. Manual acceptance is a separate record: `../10-uat/`.
