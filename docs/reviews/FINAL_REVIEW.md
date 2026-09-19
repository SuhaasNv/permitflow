# Final review

What was built, the trade-offs behind it, what the AI got wrong, and what I would defend in the debrief. Written 19 Sep 2026 at the end of Sprint 3, before the v0.3.0 release. Companion documents: `ASSESSMENT_TRACEABILITY.md` (brief line by line), `PRODUCTION_READINESS_REVIEW.md` (gaps with severity), `ISSUES_AND_MITIGATIONS.md` (what went wrong and what we did), `../../AI_USAGE.md`.

## What was built

Use cases 1 and 2 of the brief, complete: an operator applies through a four-section form with checked uploads and a progress indicator; submits; an officer reviews the full submission with the AI findings beside each document, leaves feedback tied to a section or a document (with templates), requests a resubmission; the operator sees "Pending Pre-Site Resubmission" with the comments on top and can edit only the flagged parts; resubmits as a new immutable revision; the officer is notified, sees what changed, compares any two revisions, tracks each item to resolution, schedules and completes the site visit, routes to approval and approves or rejects with a note; every step is audited and both roles see the status labels the brief prescribes. Beyond the brief and marked as such: withdrawal, draft deletion, feedback undo and reopen, a guided respond mode, search, a landing page, a licence certificate issued in the approval transaction with an officer preview, Return to review, and a custom domain for production. Use case 3 is deferred with its statuses kept in the state machine and tested.

By the numbers: 748 backend tests on a real PostgreSQL, 152 frontend tests, 8 Playwright specs (the journey, six scenarios, the accessibility gate) run in CI against the full stack, 14 AI golden cases (12 counted on the mock, 14 of 14 live) and a 21-run fairness check, 22 threats with controls, 12 ADRs, 70 stories on a Notion board mirrored in the repository, 180+ conventional commits on story branches merged `--no-ff`.

## The decisions I would defend first

1. **Scope: two use cases done properly over three done thinly.** UC1 and UC2 form one loop; a reviewer can run it end to end. UC3 would have added a checklist model and three screens at the cost of the tests, the deployment and the documents the brief asks for.
2. **The state machine as a table.** Fourteen states, actors, guards and labels as data, exhaustively tested; every status change goes through one function; the officer's available actions and the operator's labels are derived from it. This is what makes "no applications lost" a checked property rather than a hope.
3. **"Only the flagged sections" as an authorization rule, not a UI hint.** Editability is derived from open, released feedback; the server answers 403 for anything else; the UI walks the operator through exactly those targets.
4. **Immutable revisions and a read-time diff.** Every submission is a snapshot; the compare view is computed, never stored; nothing is lost between rounds by construction.
5. **AI advisory by construction.** The verifier writes only to `verification_runs`; the workflow has no AI actor; injection is handled by a deterministic rule before the verdict is read; the output passes two strict schemas; the provider sits behind an interface with a mock used in tests and CI. The Approve dialog warns about unresolved findings but never blocks: the officer decides.
6. **Same-transaction audit, notifications and licence.** A status change, its audit row, the operator's notification and (on approval) the certificate either all happen or none do.
7. **Build once, gate on a person.** CI builds two images, Railway pulls by tag, `dev` deploys automatically, `main` waits for the owner's approval, the deploy job waits for the rollout and checks health.

## Trade-offs I made knowingly

- Background tasks instead of a queue (ADR-004): a restart marks running checks failed and re-run recovers; a worker is the first infrastructure change for production.
- Local-disk files on a volume instead of object storage; in-process login limiter; JWT in `sessionStorage`; no CSP: all accepted for a demo, all listed with severity in the readiness review.
- A 14-case AI evaluation set and a 21-run name-swap fairness check, run on the mock in a six-stage gate on every push and against the live model nightly and on AI changes, with LangSmith tracing and an experiment per run: enough to catch a broken prompt and to show a history, not a benchmark; promptfoo red-teaming and Project Moonshot recorded as next steps rather than half-built.
- Hand-written frontend API types instead of OpenAPI codegen: they stayed small; drift is caught by the integration and end-to-end suites.
- Nice-to-have features on the last day (certificate, landing hero, search) before the closing documents: the assessor review called this out fairly; the documents were then written in one pass, and the features are marked beyond the brief. In a real team I would have held them behind the release.

## What the AI got wrong, briefly

The first live verifier run invented enum values and missed an expired certificate (pinned schema, date in the prompt). It proposed scope it should not have (a story for "accepting" AI findings, a full red band) and once offered a workflow option the state machine did not allow. The first certificate layout overflowed; two prompt wordings were rejected by the harness; a scratch file was swept into a commit; Notion notes carried the wrong day; two CI runs failed on a lint the AI had not run locally. Every one is in `AI_USAGE.md` with what was done about it. The design of the system was mine; the AI produced the code and the documents against that design, and every piece was tested before it counted.

## What I would show in the debrief

1. `SCOPE.md` and the sprint plan: what was cut and why.
2. `domain/workflow.py` and `tests/unit/test_workflow.py`: the table and the exhaustive test.
3. The resubmission loop in the browser with the demo documents: the planted issues caught, the flagged-only edit, the compare view, the audit trail.
4. `domain/verification_rules.py` and `evals/`: how the AI is boxed in and how it is measured.
5. `.github/workflows/deploy.yml` and the production approval in the Actions run.
6. `PRODUCTION_READINESS_REVIEW.md`: what I would not ship to a real authority yet.

## Status of the deliverables

README (setup, stack, demo accounts, security, tests, CI, deployment, AI verification, AI Usage, What I would do next), `SCOPE.md`, `AI_USAGE.md`, `CHANGELOG.md`, `docs/testing/TEST_STRATEGY.md`, `docs/ai/AI_EVALUATION.md`, `docs/operations/OPERATIONS.md`, `docs/uat/UAT_PLAN.md`, `docs/reviews/PRODUCTION_READINESS_REVIEW.md`, `docs/reviews/ASSESSMENT_TRACEABILITY.md`, `docs/reviews/ISSUES_AND_MITIGATIONS.md` and this file exist and describe what is in the repository. The index in `docs/README.md` marks each as written.
