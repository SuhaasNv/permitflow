# AI Usage

How AI tools were used to build PermitFlow, what they were given, how their output was checked, and where they were wrong. The short version is in `README.md`; this is the full record for the debrief. The AI inside the product (the document verifier) is a separate topic, covered in `docs/ai/AI_VERIFICATION_DESIGN.md` and `docs/ai/AI_EVALUATION.md`.

## 1. Tools and what each did

| Tool | Used for |
|------|----------|
| Claude Code (Anthropic's terminal coding agent), models Claude Opus 5 for most sessions and Claude Fable 5.1 for some | The pair for the whole build: solutioning documents, design system and prototype, every story's code and tests, docs, commit messages, the sprint rituals. It worked under two standing instruction files (below) and never pushed to GitHub without an explicit yes in that turn. |
| Claude Code subagents | Independent reviews run in parallel with separate briefs: two design-critique passes on the prototype (design phase), three devil's-advocate edge-case reviews (Sprint 2, `docs/reviews/EDGE_CASE_REVIEW.md`), a layout audit at five widths (`docs/reviews/LAYOUT_AUDIT.md`), three bug hunts (backend rules, frontend interaction, seams; `docs/reviews/BUG_HUNT_REVIEW.md`), a read-only audit of the Document checks counters, a read-only "strict assessor" review against the brief on the last day, and a final read-only bug hunt on the last day's changes. Reviews were read-only; fixes went through the normal story flow with tests. |
| Claude in Chrome | Two persona run-throughs in a real browser with the demo PDFs (operator, then officer, then operator again), the Railway dashboard steps that the CLI could not do (project tokens), and layout checks at phone, tablet and desktop widths. I typed every password myself; the agent never handled credentials. |
| Notion MCP | The story board ("PermitFlow, Xtremax Assessment"): status moves as stories started and finished, notes with branch names and follow-ups, kept 1:1 with `docs/planning/USER_STORIES.md`. |
| Railway MCP and CLI, GitHub CLI | Environments, variables, volumes, domains, deployments; CI runs, environment secrets, branch pushes (always after my yes). |
| OpenAI `gpt-4.1-mini` | Inside the product only: the advisory document verifier behind a provider interface, with a deterministic mock used in tests and CI. Not used to write code. |

## 2. How the work was organised (the workflow the AI worked inside)

The tools did not set the process; the process was fixed first and the tools were driven through it.

1. **Understand the problem** (17 Sep): read the brief twice, wrote `docs/discovery/PROBLEM.md` (personas, pain points, success criteria) and extracted every requirement into `docs/requirements/REQUIREMENTS.md` with ids (FR, NFR, SEC, AI, AUD, UX, REL) and the use cases into `docs/requirements/USE_CASES.md`.
2. **Define the scope** (17 Sep): `SCOPE.md` with MUST, SHOULD, COULD and DEFERRED tables, the assumptions where the brief is ambiguous, and the stack in five sentences. Use case 3 deferred with its statuses kept.
3. **Solutioning** (17 Sep): `docs/architecture/SOLUTIONING.md` (options per problem), the domain model, the state machine as a table, the first nine ADRs, the threat model, the test strategy. The AI wrote drafts against the requirement ids; I decided each option.
4. **Design phase** (17 to 18 Sep): design direction, tokens, screen and component inventories, UI states, a 23-artboard clickable prototype, two independent design-critique passes.
5. **Agile delivery** in three one-day sprints with a Notion board mirrored 1:1 by `docs/planning/USER_STORIES.md` (US-000 to US-073), a sprint plan with goals, cut order and a close ritual (`docs/planning/SPRINTS.md`), and a definition of done per story (tests, docs, Notion, env vars, migrations, ADRs, scope). Sprint 1 "An operator can submit", Sprint 2 "The loop closes, twice", Sprint 3 "Ship it honestly". Each story on its own branch from `dev`, merged `--no-ff`; `main` only at releases (`docs/operations/BRANCHING.md`).
6. **Implementation** story by story, with the per-story checklist in `CLAUDE.md` enforced every time: tests per layer, browser check at three widths, docs updated in the same change, Notion moved.
7. **CI/CD and deployment**: seven-job CI, images built once to GHCR, two Railway environments, production behind a human approval, health gates (ADR-011).
8. **Reviews**: three edge-case reviews after Sprint 2, a layout audit, three bug hunts, two persona run-throughs, a strict assessor review and a final bug hunt on the last day; every finding fixed with a test or recorded as a decision (`docs/reviews/ISSUES_AND_MITIGATIONS.md`).
9. **Documentation and release**: README, this file, production readiness, UAT, traceability and final review; then the v0.3.0 release.

## 3. The context the AI was given

Two instruction files were loaded into every session (the project one is checked in at the repository root as `CLAUDE.md`, so a reviewer can read exactly what the AI was told):

- A global `~/.claude/CLAUDE.md` with engineering standards: no `any`, typed props and state, every `useEffect` cleaned up, no unrequested refactors, propose before changes over 20 lines or several files, build and test before every commit, conventional commit subjects, never push without asking, never mention AI tools in commits.
- The repository `CLAUDE.md` (checked in) with the project rules: the three personas and that operators never receive internal status codes; the modular monolith layering (`api → services → domain / repositories → models`, `domain/` pure Python); every status change through `domain/workflow.py`; AI never mutates application state; revisions immutable and audit rows written in the same transaction; upload allowlist, size limit and magic-byte check; the error envelope; the documents that are sources of truth (`SCOPE.md`, `REQUIREMENTS.md`, `STATE_MACHINE.md`, `DOMAIN_MODEL.md`, design docs); the Notion board ids; the per-story checklist (tests, docs, Notion, env vars, migrations, ADRs, scope); the sprint close ritual; UI rules (no em dashes, no emoji or gradients, red only for the brand mark, one primary action per screen, label plus dot for every status, layouts verified at 390, 1024 and 1280).

Before any code, the solutioning documents were written and reviewed (requirements with ids, use cases, domain model, state machine, ADRs, threat model, test strategy), then a design system and a clickable prototype. The code phase started from those documents, so every prompt could point at an id (FR-024, SEC-005, T5) instead of re-describing the requirement.

## 4. Examples of prompts and instructions

Standing instructions from the two files, paraphrased, in the order the project went (the verbatim chat prompts follow):

- Scoping (standing instruction, paraphrased from `CLAUDE.md`): "Three roles, never reduce to two: operator, officer, admin (read-only oversight, beyond the brief by product decision). UC3 is deferred; the two post-site statuses must still exist in the state machine and be tested because the brief lists them."
- State machine: "All status changes go through `domain/workflow.py`. Write the transition table as data (source, target, actor, guard, label) and a test that iterates every (state, target, actor) combination and asserts allowed, forbidden or invalid."
- Resubmission: "Operator edits only the flagged sections and documents. Editability comes from open, released feedback; a section that was not flagged returns 403. Resubmit is a new immutable revision; items whose target changed become `addressed` automatically."
- Officer feedback: "Feedback is a draft until the officer requests resubmission; then it is released and frozen. Officers can resolve only items the operator has seen. Give withdraw and resolve a 10 second undo and audit the undo."
- Scope discipline (when the AI proposed a new "Accept AI finding" story): "Don't create different user stories because you are just increasing the scope." The story was dropped; the approval path was explained instead.
- Testing: "Explicitly test each workflow separately": one Playwright spec per workflow, each ending on the audit trail, plus the end-to-end journey.
- Reviews: "Deploy an agent that takes care of orientation and layouts" and later "deploy bug fixer agents" with three separate briefs; findings had to be reproduced before being reported and fixed with regression tests.
- CI/CD trade-off: "Go with the cut, GHCR is fine": one CI build of two images pushed to GHCR, Railway pulls; promptfoo, LangSmith and SAST tooling recorded under "what I would do next" rather than built.
- Deployment safety: "Production should be approved by a person": GitHub environment with a required reviewer, `main` only, health gates after the rollout.
- Product: "What if the user can download the certificate: render it on approval, let the officer preview it, let the operator download it" (US-051, marked beyond the brief in `SCOPE.md`).
- Last day: "Check Notion and all the user stories and every .md; everything should be consistent", then "rate our application like Xtremax would, a strict guy, and tell me what can be improved."


### Verbatim prompts from the sessions

Typed as they were, slang included; the AI worked from these plus the standing files. A few of many:

- "Are you checking with Notion... merging strategies... branching strategies?" (early Sprint 2; the answer became `docs/operations/BRANCHING.md` and the story-per-branch rule)
- "explicitly test each workflow separately" (US-042, one Playwright spec per workflow)
- "deploy an agent that takes care of orientation, layouts" (the layout audit, US-043)
- "Bro, I don't want you to add this. Don't create different user stories because you are just increasing the scope." (a proposed "accept AI finding" story, dropped)
- "yeah go with the cut, ghcr is fine bro, so its two images?" (ADR-011)
- "push it and go with the certificate bro and test in that branch dont merge it to dev yet please" (US-051 stayed on its branch until I had reviewed it in the browser)
- "yes push it, dont start with day 3 yet. i want you to deploy a bug fixer agents" (US-050, three parallel bug hunts)
- "what if the user can download the certification... on spot render a certificate... officer preview... user can download" (US-051)
- "make sure these are mentioned in the architecture md files and all the diagrams too" (docs in the same change, every time)
- "can you do a run through with claude in chrome for me with the actual documents you have created please." (first persona run-through; found R1 and R2)
- "keep it, do the label fix bro" (after the AI offered to revert a feature to "tighten scope": kept, one-line fix instead)
- "reject it, and then proceed with a soft option" (approval warning instead of a hard gate, keeping the advisory principle)
- "go with 1 and 2 bro" (Return to review and the prompt fix; items 3 to 5 of the scope list deliberately left)
- "now check the notion for me please and all the user stories and everything verify everything and all the .mds we have everything should be like consistent please."
- "deploy an agent to rate our application and the output and the standards we are following like how xtremax will rate me. a strict guy, and tell me what can be improved" and "one more sub agent to check for any other bugs or something."
- "i need the issues found and what are the mitigations too, because i think xtremax can ask right" (this repository's `docs/reviews/ISSUES_AND_MITIGATIONS.md`)

## 5. How output was reviewed, validated and corrected

- Every story ran the full backend suite on a real PostgreSQL (`permitflow_test`, migrations from scratch), vitest, and Playwright where a UI path changed; `ruff`, `mypy --strict` and `tsc --strict` had to be clean before a commit. CI repeats all of it, plus the AI golden set, gitleaks and dependency audits.
- Every screen was checked in the browser at 390, 1024 and 1280 before its story moved to Done; two full persona run-throughs with the demo PDFs were done on the last day and found two defects the tests had not (the licence download hidden when the approval carried no note; a misleading feedback heading). Both were fixed with tests.
- Prompt changes to the product's verifier had to pass the 14-case harness on the mock in CI and by hand against OpenAI; the harness rejected two of the three wordings tried on the last day (one left the false finding in place, one turned clean documents into `issues_found`, 11 of 14). Only the third shipped.
- Subagent reviews were treated as claims, not facts: each finding had to come with a reproduction and was re-verified before a fix; three findings were kept as product choices and documented rather than "fixed".
- Docs were checked against code at the end of each sprint and once more on the last day (API table against the routers, state machine table against `workflow.py`, test counts, dates against `git log`).
- Git hygiene: story per branch, `--no-ff` merges into `dev`, `main` only at releases; the AI proposed commit messages, I read every diff before the commit; pushes only on my explicit yes.

## 6. Where the AI was unhelpful, wrong, or produced work I discarded

- First live run of the verifier: the model invented enum values (`status: rejected`, `severity: error`) and reported an expired certificate as valid because it had no date. Fixed by pinning the vocabulary in the wire schema and passing today's date in the prompt; recorded in `docs/ai/AI_VERIFICATION_DESIGN.md`.
- The AI proposed a new user story for "accepting an AI finding" and, separately, a full red landing band; both were rejected (scope creep; too heavy) and are recorded in the story notes.
- The AI offered an approval-stage option ("add feedback and request resubmission") without checking the state machine; it was impossible from Pending Approval. That mistake led to the Return to review transition, a real gap.
- The first certificate layout overflowed on long addresses, hid the brand mark behind a plain square, and a later "sliding" signature strip collided with the footer; three iterations, each checked as a rendered PNG, before it shipped.
- A subagent's scratch test file was swept into a commit by `git add -A` while it was still running; removed and recommitted, and staging became explicit from then on.
- Notion notes were written with the wrong day (20 Sep) for events that happened on 18 and 19 Sep; corrected in the consistency pass. Two remote CI runs failed on `ruff` line length the AI had not run locally; the pre-commit routine was tightened.
- Licence dates were first computed in UTC (a day off in Singapore); fixed to `Asia/Singapore`.
- The verifier flagged the demo documents' "fictional document" footer as a possible prompt injection; it took three prompt wordings and the harness to fix without breaking the clean cases.
- The AI's own strict review on the last day scored Documentation 5/10 because the two README sections the brief names were still missing while nice-to-have features had been built; this document is part of the answer.

## 7. What I would say in the debrief

The AI wrote most of the code and the docs; the design of the system (personas, state machine as data, immutable revisions, same-transaction audit, advisory AI behind an interface, edit-only-flagged as an authorization rule) came from the solutioning phase and the standing instruction files, and every piece of generated code went through tests I can run in front of you. I can explain any file in the repository. Where I cut corners: no queue or worker for the AI checks (FastAPI background tasks, `docs/architecture/decisions/ADR-004`), local-disk uploads on a Railway volume, in-process rate limiting, no CSP on the frontend, a 14-case evaluation set. Those are listed with what I would do about them in `README.md` under "What I would do next".
