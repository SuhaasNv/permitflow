# AI Usage

How AI tools were used to build PermitFlow, what they were given, how their output was checked, and where they were wrong. The short version is in `README.md`; this is the full record. The AI inside the product (the document verifier) is a separate topic, covered in `docs/ai/AI_VERIFICATION_DESIGN.md` and `docs/ai/AI_EVALUATION.md`.

## 1. Tools and what each did

| Tool | Used for |
|------|----------|
| Claude Code (Anthropic's terminal coding agent), models Claude Opus 5 for most sessions and Claude Fable 5.1 for some | The pair for the whole build: solutioning documents, design system and prototype, every story's code and tests, docs, commit messages, the sprint rituals. It worked under two standing instruction files (below) and never pushed to GitHub without an explicit yes in that turn. |
| Claude Code subagents | Independent reviews run in parallel with separate briefs, each read-only and each required to reproduce a finding before reporting it: two design-critique passes on the prototype (design phase), three devil's-advocate edge-case reviews (Sprint 2, `docs/reviews/EDGE_CASE_REVIEW.md`), a layout audit at five widths (`docs/reviews/LAYOUT_AUDIT.md`), three bug hunts (backend rules, frontend interaction, seams; `docs/reviews/BUG_HUNT_REVIEW.md`), a logic audit of the Document checks counters, a strict assessor review against the brief, a final bug hunt on the last day's changes, and a research pass on current AI-assurance tooling (promptfoo, LangSmith, Langfuse, OpenTelemetry GenAI, Project Moonshot). Fixes never came from a reviewer; they went through the normal story flow with tests. |
| Claude in Chrome | Three persona run-throughs in a real browser with the demo PDFs (operator, officer, operator again; the third on the deployed development environment as the Sprint 3 acceptance), the DNS and Railway dashboard steps the CLI could not do (registrar records, custom domains, project tokens), the LangSmith setup (API key creation, checking traces and experiments), and layout checks at phone, tablet and desktop widths. I signed in myself every time; secrets moved from the clipboard into GitHub, Railway and `.env` through shell commands, so the agent never read a credential. |
| Notion, through its MCP server connected to Claude Code | The story board ("PermitFlow, Xtremax Assessment"): five epics (E0 foundation and delivery, UC1, UC2, UC3 deferred, E4 admin) and stories US-000 to US-073 with status, priority, sprint day and notes; status moved as stories started and finished, notes with branch names and follow-ups; kept 1:1 with `docs/planning/USER_STORIES.md`. The board was the live truth for planning, the markdown the record in the repository. |
| Railway MCP and CLI, GitHub CLI | Environments, variables, volumes, domains, deployments; CI runs, workflow dispatches, repository secrets, branch pushes (always after my yes). |
| LangSmith | Tracing of the product's verifier (off unless a key is set, inputs hidden by default) and the golden set as a dataset with one experiment per evaluation run, so a prompt change has a pass-rate history. Not used to write code. |
| OpenAI `gpt-4.1-mini` | Inside the product only: the advisory document verifier behind a provider interface, strict JSON schema on the wire, a deterministic mock in tests and the CI gate, the real model in the nightly evaluation. Not used to write code. |

## 2. How the work was organised (the workflow the AI worked inside)

The tools did not set the process; the process was fixed first and the tools were driven through it.

1. **Understand the problem** (17 Sep): read the brief twice, wrote `docs/discovery/PROBLEM.md` (personas, pain points, success criteria) and extracted every requirement into `docs/requirements/REQUIREMENTS.md` with ids (FR, NFR, SEC, AI, AUD, UX, REL) and the use cases into `docs/requirements/USE_CASES.md`.
2. **Define the scope** (17 Sep): `SCOPE.md` with MUST, SHOULD, COULD and DEFERRED tables, the assumptions where the brief is ambiguous, and the stack in five sentences. Use case 3 deferred with its statuses kept.
3. **Solutioning** (17 Sep): `docs/architecture/SOLUTIONING.md` (options per problem), the domain model, the state machine as a table, the first nine ADRs, the threat model, the test strategy. The AI wrote drafts against the requirement ids; I decided each option.
4. **Design phase** (17 to 18 Sep): design direction, tokens, screen and component inventories, UI states, a 23-artboard clickable prototype, two independent design-critique passes.
5. **Agile delivery** in three one-day sprints with a Notion board mirrored 1:1 by `docs/planning/USER_STORIES.md` (US-000 to US-073), a sprint plan with goals, cut order and a close ritual (`docs/planning/SPRINTS.md`), and a definition of done per story (tests, docs, Notion, env vars, migrations, ADRs, scope). Sprint 1 "An operator can submit", Sprint 2 "The loop closes, twice", Sprint 3 "Ship it honestly". Each story on its own branch from `dev`, merged `--no-ff`; `main` only at releases (`docs/operations/BRANCHING.md`).
6. **Implementation** story by story, with the per-story checklist in `CLAUDE.md` enforced every time: tests per layer, browser check at three widths, docs updated in the same change, Notion moved.
7. **CI/CD and deployment**: CI with backend, frontend, end-to-end (including the accessibility gate), secret scan, dependency audit and image jobs; a six-stage AI gate called from CI (model approval, contracts, golden set, adversarial, fairness, verdict); a separate live evaluation against the real model; images built once to GHCR; two Railway environments on the owner's domain; production behind a human approval; health gates after every rollout (ADR-011).
8. **Reviews**: three edge-case reviews after Sprint 2, a layout audit, three bug hunts, three persona run-throughs, a strict assessor review, a final bug hunt, and a legal, privacy and accessibility review on the last day; every finding fixed with a test or recorded as a decision (`docs/reviews/ISSUES_AND_MITIGATIONS.md`, `docs/reviews/LEGAL_AND_ACCESSIBILITY_REVIEW.md`).
9. **Documentation and release**: README, this file, AI assurance, production readiness, UAT, traceability and final review; then the v0.3.0 release.

## 3. The context the AI was given

Two instruction files were loaded into every session (the project one is checked in at the repository root as `CLAUDE.md`, so a reviewer can read exactly what the AI was told):

- A global `~/.claude/CLAUDE.md` with engineering standards: no `any`, typed props and state, every `useEffect` cleaned up, no unrequested refactors, propose before changes over 20 lines or several files, build and test before every commit, conventional commit subjects, never push without asking, never mention AI tools in commits.
- The repository `CLAUDE.md` (checked in) with the project rules: the three personas and that operators never receive internal status codes; the modular monolith layering (`api → services → domain / repositories → models`, `domain/` pure Python); every status change through `domain/workflow.py`; AI never mutates application state; revisions immutable and audit rows written in the same transaction; upload allowlist, size limit and magic-byte check; the error envelope; the documents that are sources of truth (`SCOPE.md`, `REQUIREMENTS.md`, `STATE_MACHINE.md`, `DOMAIN_MODEL.md`, design docs); the Notion board ids; the per-story checklist (tests, docs, Notion, env vars, migrations, ADRs, scope); the sprint close ritual; UI rules (no em dashes, no emoji or gradients, red only for the brand mark, one primary action per screen, label plus dot for every status, layouts verified at 390, 1024 and 1280).

Before any code, the solutioning documents were written and reviewed (requirements with ids, use cases, domain model, state machine, ADRs, threat model, test strategy), then a design system and a clickable prototype. The code phase started from those documents, so every prompt could point at an id (FR-024, SEC-005, T5) instead of re-describing the requirement.

## 4. Prompts and instructions

Two kinds. The standing instructions lived in the two `CLAUDE.md` files and applied to every session; the session prompts were typed during the work. Both are given in the form they were meant, edited for readability, and each is followed by what it produced. Grouped by the decision they carry rather than by date.

### Architecture and domain rules (standing instructions)

- "Three roles, never reduce to two: operator, officer, admin as read-only oversight. Use case 3 is deferred, but its two statuses must exist in the state machine and be tested, because the brief lists them."
- "All status changes go through `domain/workflow.py`. Write the transition table as data (source, target, actor, guard, label) and a test that iterates every (state, target, actor) combination and asserts allowed, forbidden or invalid." (588 parametrised cases; the officer's actions and their disabled reasons are derived from the same table)
- "Operators edit only the flagged sections and documents. Editability is derived from open, released feedback; a section that was not flagged returns 403. A resubmission is a new immutable revision, and items whose target changed become `addressed` automatically."
- "Feedback is a draft until the officer requests resubmission; then it is released and frozen. Officers resolve only items the operator has seen. Withdraw and resolve get a 10-second undo, and the undo is audited."
- "The AI never mutates application state, feedback or status. It writes a run row; a person decides." (the advisory principle every later AI decision was held to)
- "Modular monolith: `api` calls `services`, `services` call `domain` and `repositories`; `domain/` is pure Python with no framework or I/O imports." (enforced by a layering test)

### Scope and product decisions (session prompts)

- "Don't create a new user story for this; you are increasing the scope." (a proposed "accept AI finding" story, dropped; the approval path was explained in the UI instead)
- "What if the operator could download the licence: render a certificate on approval, let the officer preview it before deciding, and let the operator download it afterwards." (US-051, marked beyond the brief in `SCOPE.md`, kept on its branch until I had reviewed the rendered PDF)
- "Keep the feature and fix its label instead of reverting it." (after the AI offered to remove a feature to tighten scope)
- "Reject this application, then add a warning at approval rather than a hard block." (the Approve dialog warns about unresolved checks and stays enabled, so the officer decides)
- "Add Return to review and fix the verifier prompt; leave the other three scope items." (two of five proposed items taken; the rest recorded, not built)
- "One naming convention per environment on the domain: `permitflow.space` and `api.` for production, `dev.` and `api.dev.` for development; keep the platform hosts as fallbacks." (US-052)

### Quality, reviews and evidence (session prompts)

- "Test each workflow separately, one Playwright spec per workflow, each ending on the audit trail." (US-042)
- "Deploy a review agent for orientation and layouts at every width." (`docs/reviews/LAYOUT_AUDIT.md`)
- "Deploy three bug-hunt agents with separate briefs: backend rules, frontend interaction, the seams between them. Reproduce before reporting." (US-050, 45 findings, 43 fixed, 2 kept as decisions)
- "Do a run-through in the browser with the real demo documents, as each persona, and take notes on every step." (three run-throughs; the first found two defects the tests had missed, the third was the Sprint 3 acceptance on the deployed environment)
- "Review the application, its output and the standards we follow as a strict assessor would, against the brief, and report what can be improved." (`docs/reviews/PRODUCTION_READINESS_REVIEW.md`; it scored documentation 5/10, which produced the README sections and this file)
- "Check Notion, every user story and every document against each other and against the code; everything must be consistent." (the consistency pass before the release: dates against `git log`, API table against the routers, state table against `workflow.py`)
- "Record every issue found and its mitigation." (`docs/reviews/ISSUES_AND_MITIGATIONS.md`)
- "Raise unit and integration coverage of the business logic to about 80 percent, measured with every source file counted, testing behaviour rather than buttons, and enforce it in CI." (US-053: frontend 47 to 80.5 percent statements, backend 96 percent, thresholds in both jobs)

### Delivery and operations (session prompts)

- "Keep Notion in step with the work, and define the merging and branching strategy." (`docs/operations/BRANCHING.md`: story per branch from `dev`, `--no-ff` merges, `main` only at releases)
- "Take the cut: build the images once in CI and push them to GHCR; Railway pulls." (ADR-011)
- "Production must be approved by a person." (GitHub environment with a required reviewer, `main` only, health gates after the rollout)
- "Make sure every change is reflected in the architecture documents and the diagrams too." (docs in the same change, every time)

### AI assurance (session prompts)

- "If someone asks how we know the verifier's output is legitimate, the answer must be a pipeline, not a paragraph: a separate evaluation against the real model, tracing, and the AI checks as a gate of their own." (US-054 nightly and on-change live evaluation, blocking at 14 of 14; US-055 LangSmith tracing with inputs hidden by default; US-056 the six-stage AI gate called from CI)
- "Add a fairness check: the same document with the applicant's and the business's names swapped across Singapore's communities must get the same verdict." (21 name-swapped runs, mock and live, both blocking; the first live run's two differences were a harness fault and are recorded as such in `docs/ai/AI_ASSURANCE.md`)

### Legal, privacy and accessibility (session prompt, in full)

Given in full because the AI's first move was to audit the code and cut the list down before building anything: "I do not want the website to expose me legally, so please: add a privacy policy page, a terms and conditions page, and a cookie policy. Check if I need cookie consent, and add a refund policy and form consent. Only connect necessary data. Check analytics tracking. Check third-party embeds. Make the site accessible. Add alt text. Check colour contrast and make forms keyboard-friendly. Use clear button labels. Remove fake reviews. Remove unsupported claims. Add business details and check copyright on images. Check applicable local laws and flag any other risks, and make no mistakes. Create a user story for this, and put it in a document so that the reviewer can see it."

The audit found no cookies, no analytics, no embeds, no images and no reviews, so five items became "not applicable, and here is why". The work that remained: policies written from the code with PDPA framing, two demonstration-only notices, self-hosting the fonts (the browser's one third-party request), an axe-core gate over 22 screen states that found and fixed four landmark, skip-link and contrast defects, and `docs/reviews/LEGAL_AND_ACCESSIBILITY_REVIEW.md` (US-057). Two decisions were mine when asked: operator named with the repository link and no email; fonts self-hosted rather than disclosed.

## 5. How output was reviewed, validated and corrected

- Every story ran the full backend suite on a real PostgreSQL (`permitflow_test`, migrations from scratch), vitest, and Playwright where a UI path changed; `ruff`, `mypy --strict` and `tsc --strict` had to be clean before a commit. CI repeats all of it with coverage thresholds, plus the six-stage AI gate, the accessibility gate, gitleaks and dependency audits; the live model is evaluated nightly and on every change to the AI module.
- Every screen was checked in the browser at 390, 1024 and 1280 before its story moved to Done; two full persona run-throughs with the demo PDFs were done on the last day and found two defects the tests had not (the licence download hidden when the approval carried no note; a misleading feedback heading). Both were fixed with tests.
- Prompt changes to the product's verifier had to pass the 14-case harness on the mock in CI and against OpenAI; the harness rejected two of the three wordings tried on the last day (one left the false finding in place, one turned clean documents into `issues_found`, 11 of 14). Only the third shipped. The 21-run fairness check was added after that and passes on the live model.
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
- The first fairness run reported 2 of 21 name-swapped cases as differing, and the AI's first reading was "the model is sensitive to names". It was the harness: the form still carried the baseline applicant's email and the document its upper-case director line, so the model was right that form and document disagreed. Two more swaps and it was 21 of 21, twice. Recorded in `docs/ai/AI_ASSURANCE.md` because a fairness check that hides that would be measuring the wrong thing.
- Two configuration slips on the last day: a vitest coverage option that the installed version had removed (caught by `tsc -b` in the build, not by the test run), and a repository secret set from the wrong `.env` file, so the first live evaluation ran with an empty key and refused, as designed. Both fixed within the hour.
