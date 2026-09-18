# SCOPE.md — PermitFlow MVP

**Assessment:** Regulatory and Licensing Platform, 3 calendar days.
**Decision in one line:** build Use Case 1 (Operator Submission & Resubmission) and Use Case 2 (Officer Review & Feedback) as one polished, tested, deployed vertical slice; support the full 12-state lifecycle in the state machine; defer Use Case 3 (On-Site Assessment checklist) with an honest description of what production would need.

## Why this scope

The assessment evaluates scope judgement, production readiness, AI usage, code quality and documentation, not feature count. UC1 and UC2 are two halves of one loop (submit → review → feedback → resubmit → compare). Building both makes the product coherent: every screen has a counterpart, every status change has a consumer, and the hardest engineering problems in the brief (immutable revisions, targeted resubmission, diffing, feedback resolution tracking, audit trail, role-specific status visibility, AI verification with graceful failure) all live inside this loop. UC3 adds a second, structurally similar loop (checklist items ↔ targeted clarification) whose value is mostly repeating patterns already proven in UC1/UC2.

## Tech stack and architecture (3–5 sentences)

A modular monolith: a FastAPI + SQLAlchemy 2 + Pydantic v2 backend on PostgreSQL, and a React 19 + TypeScript (strict) + Vite + Tailwind frontend using TanStack Query, React Hook Form and Zod. The backend is organised by domain module (auth, applications, revisions, documents, verification, feedback, notifications, audit) with a single explicit state machine owning all status transitions and server-side authorization on every application-scoped endpoint. AI document verification runs asynchronously in-process behind a provider interface (OpenAI structured outputs via the official SDK, plus a deterministic mock used in tests and when no API key is configured) and its output is schema-validated and post-processed by deterministic rules before persistence; AI never changes authoritative workflow state. Files live on local disk behind a storage interface; notifications are in-app records. Tests are pytest (unit + integration against Postgres), Vitest, and a Playwright critical-journey E2E, all run in GitHub Actions; deployment targets Railway.

## MUST HAVE (the vertical slice)

| # | Feature | Assessment ref |
|---|---------|----------------|
| M1 | Public landing page, email/password login, roles operator and officer with seeded accounts and role-specific home screens; the `admin` role value exists but its account and screens are S7 | roles (implied) |
| M2 | Operator: create application, sectioned form with validation, save draft | UC1 form entry |
| M3 | Operator: drag-and-drop document upload with document type; validation by extension + MIME allowlist (PDF, PNG, JPG, JPEG, TXT), magic bytes and 10 MB cap; `sha256` per file so an identical re-upload is detected as no change; PDF recommended (only machine-readable format) | UC1 uploads |
| M4 | Per-document AI verification with live status (pending → running → result), structured issues, graceful "unavailable" | UC1 real-time AI status; UC2 AI results visible |
| M5 | Progress indicator (sections + required documents) | UC1 |
| M6 | Submit → Revision 1 → `application_received` | UC1 |
| M7 | Role-specific status labels enforced by the API serializer, per the assessment table | UC2 status mapping; UC3 constraint |
| M8 | Officer queue + full application view (sections, documents, AI results) | UC2 review |
| M9 | Officer feedback linked to section or document; comment templates | UC2 feedback |
| M10 | Status transitions via explicit state machine with server-side role checks; all 12 assessment states + `draft`; site visit, route to approval, approve/reject with a note so the lifecycle completes; reject possible from every non-terminal post-submission state so nothing gets stuck | UC2 status mapping; UC2 "no applications lost" |
| M11 | Operator resubmission: feedback on top, each item anchored to its section/document (click to jump), only flagged sections/documents editable, new immutable revision | UC1 resubmission |
| M12 | Officer resubmission view: changed sections highlighted, revision compare (field-level + document-level diff), feedback resolution tracking (open → addressed → resolved) | UC2 resubmission management |
| M13 | Unlimited rounds; revision history and prior comments visible to both roles | UC1/UC2 multi-round |
| M14 | Append-only audit trail (status, submissions, feedback, documents) visible to officers | UC2 QA |
| M15 | In-app notifications on status change (to operator) and resubmission (to officers) | UC2 |
| M16 | Server-side authorization: operators cannot access others' applications; officer-only endpoints | security (implied by roles) |
| M17 | Error handling and input validation on all key paths; consistent API error shape | Submission checklist |
| M18 | Tests: state machine, authorization, diff, AI output validation, lifecycle integration, E2E critical journey | production readiness |
| M19 | CI (lint, typecheck, tests, secret scan) and Railway deployment with health endpoint | production readiness |
| M20 | README (with AI Usage and What I would do next), SCOPE.md, architecture docs | Submission checklist |

## SHOULD HAVE (simplified if time is short)

| # | Feature | Simplification |
|---|---------|----------------|
| S1 | Officer queue filtering by status | Client-side filter over a single list endpoint; the queue itself is M8 |
| S2 | Re-run AI verification action for a document · **done in Sprint 1 (operator) and Sprint 2 (officer)** | Same code path as upload; the live status itself is M4 |
| S3 | Operator can delete a document while in draft | Simple DELETE; without it a wrong upload is fixed by replacing the type |
| S4 | Compare any two revisions (not only current vs previous) · **done in Sprint 2** | Same diff function; only the selector changes |
| S5 | AI evaluation dataset + runner script | Six fixtures, manual run documented |
| S6 | Structured request logging with request id | Middleware only, no log shipping |
| S7 | Admin persona: seeded admin account, `/admin/*` router, an operations dashboard (counts by status, idle applications, AI verification health, cross-application audit feed, read-only application view) and **user management** (create user, change role, deactivate/reactivate; every change audited; the last active admin cannot be demoted or deactivated). **Beyond the brief** — added because a regulator operating the platform needs oversight and account control; the assessment names only Operator and Officer. The `admin` role value exists in the enum from Day 1 (cheap); everything else in this row is built only after the MUST list is Done, so cutting it removes a router and two pages, not a concept. | Overview page first; user management second (US-073); no password reset or self-registration |

## COULD HAVE (only if the core is stable)

| # | Feature |
|---|---------|
| C1 | Operator dashboard summary (counts by status) · **done in Sprint 1** as a one-line summary and grouped work cards, not KPI tiles |
| C2 | Officer assignment (assign application to an officer) |
| C3 | Image OCR for document verification (currently images are marked "not extractable") |
| C4 | Download all documents as a bundle |
| C6 | Licence certificate issued on approval, officer preview, PDF download · **built 19 Sep (US-051)** on its own branch, merged after review |
| C5 | Operator withdraws a submitted application with an optional reason · **done 19 Sep (US-038)**: new terminal status, officers notified, audited |

## DEFERRED / MOCKED

| Item | Status | Why | What production would need |
|------|--------|-----|----------------------------|
| UC3 site-visit checklist, draft save, per-item "Need Further Clarification", operator targeted response, per-item clarification rounds | **Deferred** (state transitions for site visit states are implemented; checklist UI/data model is not) | Second loop with the same shape as UC1/UC2; building it well would take the time needed to make UC1/UC2 production-quality. The state machine already contains the post-site states so adding UC3 is additive. | `Checklist`, `ChecklistItem`, `ClarificationRequest`, `ClarificationResponse` entities; officer checklist screen with draft autosave; operator flagged-items screen; auto transition on checklist submit. Estimated 1.5 days. |
| Email / SMS notification delivery | **Mocked** (in-app notification records; an email adapter logs the message instead of sending) | Delivery is a vendor integration, not a product problem. | Transactional email provider (e.g. SES/Postmark) behind the existing `Notifier` interface, retry queue, unsubscribe handling. |
| Background job queue for AI verification | **Simplified** (FastAPI `BackgroundTasks` in-process; status polled by the client) | A broker adds operational surface for no demo benefit. The provider interface and the `verification_runs` table are queue-ready. | Redis/RQ or Celery worker, or Postgres `SKIP LOCKED` queue; retry policy; dead-letter visibility. |
| Object storage for uploads | **Simplified** (local disk behind `FileStorage`; Railway volume in deployment) | S3 credentials and signed URLs are integration work. | S3-compatible bucket, server-side encryption, signed download URLs, virus scanning. |
| User registration, password reset, MFA, SSO | **Omitted** (seeded users, login only) | Identity is not what the assessment evaluates. | OIDC integration (e.g. a national digital identity provider), MFA, session management. |
| Multiple licence types / configurable forms | **Omitted** (one licence type, form schema defined in code and shared with the frontend) | Form-builder is a product in itself. | Form definitions in the database, versioned; renderer driven by schema. |
| Image OCR | **Omitted** (images accepted and stored; verification returns `unreadable` with an explicit reason) | OCR is a dependency and cost decision. | Vision-capable model or OCR service, with cost controls. |
| Real-time push (WebSocket/SSE) for verification status | **Simplified** (polling every 2 s while any document is verifying) | Polling meets "real-time status visible" at MVP scale. | SSE endpoint or WebSocket with reconnect. |
| Rate limiting, WAF, DDoS protection | **Simplified** (in-memory limiter on auth endpoints) | Infra-level concern. | Edge rate limiting, WAF rules. |
| Officer assignment / workload routing | **Omitted** | Not in the acceptance criteria. | Assignment model, queue ownership, reassignment audit. |
| Virus scanning of uploads | **Omitted** (type/size allowlist and magic-byte check only) | Requires ClamAV or a vendor. | Scan on upload, quarantine state. |

## Assumptions (where the assessment is ambiguous)

1. **Licence type:** one licence type, "Food Establishment Licence", with four form sections and four required document types. The assessment does not name a licence.
2. **Pre-submission state:** a `draft` state exists before Application Received. The assessment's table starts at Application Received; a draft is necessary for "save and return" and is never shown to officers.
3. **Under Review trigger:** Application Received → Under Review happens when an officer explicitly clicks "Start review" (so the actor is recorded in the audit trail). The assessment does not say who triggers it.
4. **Requesting resubmission requires feedback:** an officer cannot set Pending Pre-Site Resubmission with zero open feedback items.
5. **Resubmission requires a change:** an operator cannot resubmit without changing at least one flagged section or document.
6. **Site visit without checklist:** because UC3 is deferred, Site Visit Done may transition directly to Pending Approval. The post-site clarification states remain in the state machine but are unreachable in the MVP UI; the transitions exist and are unit-tested for when UC3 is built.
7. **Feedback resolution:** "addressed" is automatic (the linked section/document changed in the next revision); "resolved" is an explicit officer action. This matches "Resolution of previously flagged issues is tracked" without letting the system guess correctness.
8. **Notification channel:** in-app notification centre; email is mocked.
9. **AI verification scope:** the model checks whether the document plausibly is the declared type, whether key fields (e.g. business name, address) match the form, and whether obvious required information is missing. It does not attempt legal validity checks.
10. **Who the operator is:** the operator is the person who fills in and submits the application. One account is one person, and applications belong to the account that created them. There is no organisation or business-owner entity: the business is described by the Business section of the form. The platform does not verify that the person is authorised to act for that business; in production that check is the national business identity service. Accounts are seeded (registration, password reset and SSO are omitted, see Deferred), which matches an assessment brief that names only Operator and Officer.
11. **Admin persona:** the brief names Operator and Officer only. We add an Admin role for oversight, monitoring and user management (S7). It never changes application state, so it does not affect the assessment's workflow or visibility rules; user changes are audited.
12. **Feedback freeze:** officers can add or withdraw feedback only while the application is Under Review. Requesting resubmission releases that round's feedback to the operator and freezes it; this is what makes "edit only the flagged sections" safe (no item can disappear under an operator mid-edit).
13. **"Only flagged sections" is enforced, not just suggested:** the API rejects changes to non-flagged sections during resubmission (403). We read the brief's "operator updates only the flagged sections" as a rule that protects the officer's review scope; the trade-off is that an operator who spots their own mistake elsewhere must wait for the officer to flag it. Documented as a product decision open to reversal.
14. **Drafts are not records:** a draft that was never submitted can be deleted outright by its owner (rows, files and audit events). Only submission creates the licensing record; after that an application can be withdrawn but never deleted (US-045, 19 Sep).
15. **Document slots:** exactly one current document per required type; no free-form "other" slot in the MVP (feedback targets a type, and multi-file slots would need per-file targets).
16. **Third-party AI processing:** extracted document text (capped) and the relevant form section are sent to OpenAI for verification. This is a data-transfer decision a regulator would have to approve; the MVP documents it and the production gap (region, retention, redaction) in the threat model rather than pretending it is solved.

## Design phase (17–18 Sep 2026)

A UI/UX design phase was run between solutioning and implementation: design direction, design system, clickable prototype (23 artboards) and design documentation in `docs/design/`. It changed no MUST item; it added the public landing page to M1, expanded S7 with user management, and fixed the upload validation wording in M3.

## Sprint 1 check (18 Sep 2026)

Re-read at the Sprint 1 close: M1 to M7 and M16, M17 are built for the operator side; M18 (tests) and M19 (CI skeleton) are partial by plan; nothing was added to or removed from MUST; S2 (re-run check) and S3 (delete while draft) landed with M3/M4; C1 landed as part of the dashboard redesign. No scope change.

## Sprint 2 check (19 Sep 2026)

Re-read at the Sprint 2 close: M8 to M15 (officer review, feedback, resubmission, compare, resolution, outcome, audit, notifications) are built and verified in the browser; M2 (OpenAI provider) is live with `gpt-4.1-mini`; S2 (officer re-run) and S4 (any-two-revision compare) landed. Two stories were added for the edge-case pass (US-033, US-034); nothing was removed from MUST. Assumption 10 (who the operator is) was written down. Remaining MUST items are the E2E half of M18, the Playwright, Docker-build and deployment half of M19, and M20 (final documents), all Sprint 3.

## What "done" means for this MVP

A reviewer can clone the repo, follow the README, log in as an operator and an officer, and complete two full rounds of submission → review → resubmission → comparison, with AI verification running (or explicitly unavailable), all covered by passing CI. See `docs/planning/DEFINITION_OF_DONE.md`.
