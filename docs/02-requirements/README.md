# 02 Requirements

Written 17 Sep 2026 from `../01-discovery/PROBLEM.md` and the brief. Every requirement has an id, and those ids are what the rest of the repository points at: user stories, screens, tests and the traceability document all cite FR-, NFR-, SEC-, AI-, AUD-, UX- and REL- numbers rather than re-describing the requirement.

| Document | What it holds |
|----------|---------------|
| `REQUIREMENTS.md` | Functional (FR), non-functional (NFR), security (SEC), AI (AI), audit (AUD), UX (UX) and release (REL) requirements, each with its assessment reference and scope status |
| `USE_CASES.md` | The personas and the use cases UC0-A to UC4-A, grouped the way the Notion board groups its epics (E0 foundation, UC1, UC2, UC3 deferred, E4 admin), each with preconditions, main flow, alternatives and the requirements it exercises |

How to use it: find the id you need here, then follow it. `../../SCOPE.md` says whether it is MUST, SHOULD, COULD or deferred; `../05-planning/USER_STORIES.md` says which story delivered it; `../11-reviews/ASSESSMENT_TRACEABILITY.md` says where it is implemented, tested and evidenced.
