# 11 Reviews

Every review run on the product, and the two documents that close the assessment: the traceability against the brief and the final review. Reviews were run by independent agents with separate briefs, each required to reproduce a finding before reporting it; fixes went through the normal story flow with tests. Nothing here is a plan; each file records what was found and what happened to it.

| Document | When | What it holds |
|----------|------|---------------|
| `EDGE_CASE_REVIEW.md` | Sprint 2, 18 Sep | Three devil's-advocate reviews of the Sprint 1 code (operator journey, backend and workflow, product gaps): 47 items, what was fixed (US-033, US-034) and what was kept |
| `LAYOUT_AUDIT.md` | 19 Sep | Every route at 390, 820, 1024, 1280 and 1440: overflow, clipping, sticky elements, tap targets; findings as US-043 and US-044 |
| `BUG_HUNT_REVIEW.md` | 19 Sep | Three parallel bug hunts (backend rules, frontend interaction, the seams): 39 findings, 36 fixed, 3 kept as decisions; the browser run-through findings R1 to R12 |
| `LEGAL_AND_ACCESSIBILITY_REVIEW.md` | 19 Sep | The legal, privacy and accessibility checklist answered item by item with evidence (US-057); laws considered; the axe gate |
| `ISSUES_AND_MITIGATIONS.md` | 19 Sep | One table across all reviews and run-throughs: issue, where found, risk, mitigation, evidence; what was kept as a decision |
| `PRODUCTION_READINESS_REVIEW.md` | 19 Sep | The gap list for a real licensing authority with severity per row, what is in place, what production would need; go or no-go |
| `ASSESSMENT_TRACEABILITY.md` | 19 to 20 Sep | The brief decoded; every deliverable and acceptance criterion mapped to implementation, test and evidence |
| `FINAL_REVIEW.md` | 19 Sep, numbers refreshed 20 Sep | What was built, the decisions to defend, the trade-offs, what the AI got wrong, what to show in the debrief |

If you have ten minutes: `ASSESSMENT_TRACEABILITY.md` for "did it do what was asked", then `PRODUCTION_READINESS_REVIEW.md` for "what is missing before a real go-live". The security review sits in `../06-security/` because it is organised by control rather than by review.
