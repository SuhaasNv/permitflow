# Architecture decision records

Twelve decisions, each in the same shape: context, the options considered with their trade-offs, the decision, why, the consequences, how it is validated, and amendments dated as the code changed. Read them in three groups.

## How to read

- **The shape** (001 to 003): what the system is made of.
- **The rules** (004 to 008): the behaviours that make the brief's guarantees true.
- **The delivery** (009 to 012): stack, pipeline, and the one feature that is a record in its own right.
- **Use case 3** (013): the site visit arranged inside the case (part 1, built); the checklist and clarification parts follow as they land.

Each line below is the decision in one breath: chose X over Y because Z.

## The shape

| ADR | Chose | Over | Because |
|-----|-------|------|---------|
| [001 Modular monolith](ADR-001-modular-monolith.md) | One backend application in strict layers (api → services → domain → repositories → models), with the AI verifier as an isolated module | Microservices, or one flat application | The hard problems are business rules that want one transaction and one place to read them; a layering test keeps the layers honest; the AI module can be extracted later without a rewrite |
| [002 PostgreSQL with JSON snapshots](ADR-002-postgres-relational-with-json-snapshots.md) | PostgreSQL only; relations for users, applications, feedback and audit; each submitted revision as an immutable JSON snapshot | SQLite for convenience, or storing diffs instead of snapshots | Row locks, UUIDs and JSONB in one engine; a snapshot per revision makes "nothing is lost between rounds" true by construction |
| [003 Explicit state machine](ADR-003-explicit-state-machine.md) | The fourteen statuses and every allowed move as a data table (from, to, actor, guard, label), consulted by one function | Status changes scattered through services, or a workflow library | A table can be compared with the brief line by line and tested exhaustively (588 combinations); adding a status is a row, not a code path |

## The rules

| ADR | Chose | Over | Because |
|-----|-------|------|---------|
| [004 In-process AI verification](ADR-004-async-in-process-ai-verification.md) | Background task inside the API, result polled every 2 s, interrupted checks marked failed on restart, re-run available | A synchronous check during upload, or a broker and worker fleet | The requirement (live status per document) is met without a broker to run and explain in three days; the single entry point makes the move to a worker a call-site change |
| [005 Server-side authorization and role views](ADR-005-server-side-authorization-and-role-views.md) | Role checked per router, ownership enforced in the one function that loads an application (404 for other owners), a separate response model per role | Checking roles in the UI, or one shared response shape with fields hidden client-side | The rule "operators never see internal status codes" becomes a compile-time and test-time property, not a hope |
| [006 AI advisory with structured output](ADR-006-ai-advisory-structured-output.md) | A provider interface (OpenAI and a deterministic mock), strict wire and domain schemas, deterministic rules after the model, results that never touch status | Letting the model's answer drive the workflow, or free-text answers parsed by hand | The brief says AI assists and the officer decides; strict schemas and rules make a bad answer a flagged answer, never a state change |
| [007 Immutable revisions, read-time diff](ADR-007-immutable-revision-snapshots-and-read-time-diff.md) | Every submission is a frozen snapshot; the comparison between revisions is computed when asked; only flagged targets may change on resubmission (403 otherwise) | Editing one mutable record, or storing diffs | Auditability and "edit only the flagged sections" become server-enforced facts; the officer's compare view can never disagree with what was submitted |
| [008 Append-only audit in the same transaction](ADR-008-append-only-audit-log-same-transaction.md) | Audit rows (and notifications, and the licence on approval) written in the same database transaction as the change; no update path, and the only delete is the purge of an unsubmitted draft | A separate logging pipeline, or database triggers | A change without its audit row cannot exist and vice versa; the trail carries product meaning officers can read |

## The delivery

| ADR | Chose | Over | Because |
|-----|-------|------|---------|
| [009 Stack and delivery pipeline](ADR-009-stack-and-delivery-pipeline.md) | FastAPI + SQLAlchemy 2 + Pydantic v2 + PostgreSQL; React 19 + TypeScript strict + Vite + TanStack Query + React Hook Form + Zod; pytest, vitest, Playwright; GitHub Actions; Railway | Full TypeScript (Next.js + Prisma + tRPC), or Django + HTMX | Pydantic validates both the HTTP boundary and the model's output; TanStack Query and Zod fit polling and inline validation; everything is mainstream and explainable |
| [010 Licence certificate in the approval transaction](ADR-010-licence-certificate-in-approval-transaction.md) | Render the PDF on approval, store the bytes with a hash, audit the issue; preview in memory with a watermark | Re-rendering on every download, or rendering in the browser | An issued document must never change after issue and must be attributable; a storage failure leaves the application unapproved rather than approved without a certificate |
| [011 Delivery pipeline, two environments](ADR-011-delivery-pipeline-two-environments.md) | CI builds two images once to GHCR; Railway pulls by tag; `dev` deploys development automatically, `main` deploys production after a person approves; the job waits for the rollout and gates on health | Railway building from the repository on push, or the same plus promptfoo, tracing, SAST and staging | The tested artefact is the deployed artefact; rollback is a tag; a green CI on a weekend cannot change production; promptfoo and image scanning stay next steps, while the AI gate, live evaluation, tracing and blocking audits were built on the last day (amendments) |
| [012 Abuse limits](ADR-012-abuse-limits-in-process-and-database.md) | Per-client sliding windows in process for request rate and sign-in attempts; quotas for drafts and daily model calls counted in the database; over quota a check is stored unavailable, never a blocked application | Relying on the platform, or Redis-backed windows | Cost is counted where the truth lives; the deployment is one process, so the edge, not the app, is the answer to a distributed attack; refusing a model call is safe because the check is advisory |
| [014 Administrator read-only and user management](ADR-014-administrator-read-only-and-user-management.md) | The administrator reads every case through the officer's read routes and screens with `actions[]` empty by construction, and writes only users (role, active flag, creation) under a lock on the admin rows with protected demonstration accounts | A separate administrator case API; a super-role with officer powers | One read model per case and one authorization test per endpoint; the server never offers an administrator a transition; "never zero administrators" holds under concurrent changes |
| [013 Site visit appointment](ADR-013-site-visit-appointment.md) | The appointment is a record inside Site Visit Scheduled with its own small state (proposed, counter-proposed, confirmed, done) and immutable rounds; one workflow guard (`visit_confirmed`), six proposals at most, the officer holds the closing move and a three-working-day silence rule | New statuses, or a bare date field | The brief's status list stays intact and every consumer of it untouched; a bounded loop with an officer-only close means no case waits forever; rounds as rows give the audit trail, both histories and the checklist one source |

## Amendments as built (19 Sep 2026)

- 003: `withdrawn` state (operator, US-038); Return to review from Pending Approval (US-031 follow-up).
- 006: enums pinned in the wire schema and today's date in the prompt after the first live run; status settled from the issue list; prompt 2026-09-19.3 excludes template disclaimers from injection.
- 007: resolve only released feedback, 15 s undo (US-039); Not fixed reopens an addressed item (US-049); re-confirming declarations counts as a change.
- 006: LangSmith tracing behind a key, inputs hidden by default, in `infra` only (US-055).
- 009: frontend types hand-written rather than generated from OpenAPI; the delivery half of the decision moved to 011.
- 011: the AI checks moved from a `ci.yml` job into the reusable six-stage `ai-gate.yml` (US-056); a separate live evaluation workflow runs nightly and on AI changes (US-054); the dependency audit is blocking and `bandit` was added, and the image job waits for it (US-058).

- 011, 20 Sep: the observability layer (US-077) adds three Railway services (Prometheus, Grafana, the Telegram bot) from public images with their configuration in variables, so the "Railway never builds" rule holds without a new image; `docs/13-observability/OBSERVABILITY.md`.

## In a debrief

Name three: 003 (the workflow is a table you can test exhaustively), 006 (the AI is boxed in: schema, rules, no authority) and 011 (build once, promote by tag, a person approves production). Point at this page for the rest.
