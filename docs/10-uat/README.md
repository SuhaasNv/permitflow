# 10 User acceptance testing

Acceptance scenarios run by a person in a browser against a deployed environment, with the result of every run recorded. The automated form of each scenario exists in `frontend/e2e/`; the manual pass exists to see what the tests cannot: wording, layout, the feel of a round trip.

| Document | What it holds |
|----------|---------------|
| `UAT_PLAN.md` | Environments and accounts, the sixteen scenarios (U1 to U16) with their steps and expected results, the record of every run: local, development, CI, production after v0.3.0, the two-device UC3 run and the route smoke test of 21 Sep, and the API-level edge-case driver (`backend/scripts/uat_edges.py`, 246 checks) |

Demo material for the runs: `../12-demo/documents/` (the PDFs the scenarios upload). Findings from the runs and what was done about them: `../11-reviews/ISSUES_AND_MITIGATIONS.md`.
