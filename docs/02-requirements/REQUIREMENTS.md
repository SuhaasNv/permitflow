# PermitFlow: Requirements

Each requirement maps to the assessment brief (kept outside the repository) where possible. "Assessment ref" uses: UC1 (Operator Submission & Resubmission), UC2 (Officer Review & Feedback), UC3 (On-Site Assessment), SUB (Submission Checklist), EVAL (How You Will Be Evaluated). Items marked *engineering assumption* are ours.

Scope status per requirement is tracked in `SCOPE.md` and, at the end, in `docs/11-reviews/ASSESSMENT_TRACEABILITY.md`.

## 1. Functional requirements

| ID | Requirement | Assessment ref |
|----|-------------|----------------|
| FR-001 | An operator can create a new licence application (single licence type: Food Establishment Licence). | UC1 Initial Submission; licence type is an engineering assumption |
| FR-002 | The application form is divided into named sections; each section has typed fields with validation (required, format, length). | UC1 "Complete form data entry" |
| FR-003 | An operator can save a draft and return to it later. A section can be saved while required fields are still empty (only format and type errors block a draft save); completeness and submission require every required field. | Implied by UC1 progress indicator; engineering assumption |
| FR-004 | An operator can upload documents by drag-and-drop (and by file picker), each tagged with a document type from a required-documents list. | UC1 "Document uploads with drag-and-drop" |
| FR-005 | Each uploaded document shows an AI verification status (pending, running, verified, issues found, needs review, unreadable, failed, unavailable: defined in `docs/03-architecture/DOMAIN_MODEL.md`) that updates without a page reload. | UC1 "Real-time AI verification status visible per uploaded document" |
| FR-006 | The form shows an overall completion progress indicator (sections complete, required documents uploaded). | UC1 "Progress indicator" |
| FR-007 | An operator can submit the application when all required sections and documents are present; submission creates Revision 1 and moves status to Application Received. | UC1 |
| FR-008 | Status labels shown to a user depend on the user's role, exactly per the assessment's mapping table. | UC2 Status Mapping |
| FR-009 | When status is Pending Pre-Site Resubmission, the operator sees officer feedback prominently at the top of the application. | UC1 Resubmission Workflow |
| FR-010 | Each feedback item is linked to a specific form section or a specific document type (the slot, stable across file replacements). Operators see feedback only after the officer requests resubmission. | UC1, UC2 "contextual comments" |
| FR-011 | On resubmission, only sections/documents with open feedback are editable; other sections are read-only and carried forward unchanged. | UC1 "Operator updates only the flagged sections" |
| FR-012 | Resubmission creates a new immutable revision (N+1) and moves status to Pre-Site Resubmitted. Previous revisions are never modified. | UC1 Multi-Round; UC2 "no applications lost" |
| FR-013 | Unlimited feedback/resubmission rounds are supported. | UC1, UC2 |
| FR-014 | Revision history and all previous officer comments remain visible to both roles. | UC1 "Revision history and previous Officer comments are visible" |
| FR-015 | An officer sees a review queue listing all applications with internal status, applicant, last activity, and open feedback count; filterable by status. | UC2 Application Review; engineering assumption on columns |
| FR-016 | An officer can open any application and see all form data by section and all documents, organised. | UC2 "Officer accesses full submission" |
| FR-017 | An officer sees AI verification results and flagged document issues per document. | UC2 "AI verification results ... visible" |
| FR-018 | An officer can add feedback items with free text or from predefined comment templates, each linked to a section or document type. Feedback can be created or withdrawn only while the application is Under Review; requesting resubmission releases the round's feedback to the operator. | UC2 Feedback Workflow; freeze rule is an engineering assumption that prevents stuck applications |
| FR-019 | An officer can change application status through allowed transitions only (see `docs/03-architecture/STATE_MACHINE.md`), including rejecting from any non-terminal post-submission state so no application can be stuck. | UC2 Status Mapping; UC2 "no applications are lost" |
| FR-020 | A status change by an officer creates an in-app notification for the operator. | UC2 "Setting application status triggers automatic operator notification" |
| FR-021 | A submission or resubmission creates an in-app notification for all officers. | UC2 "Officer receives notification when case moves to Pre-Site Resubmitted"; initial-submission notification is an engineering assumption |
| FR-022 | On a resubmitted application, sections and documents that changed since the previous revision are highlighted for the officer. | UC2 "Updated sections are highlighted; only changes are surfaced" |
| FR-023 | An officer can compare the current revision with any previous revision field by field and document by document. | UC2 "compare current submission against previous versions" |
| FR-024 | Each feedback item has a resolution state (open → addressed → resolved, or withdrawn; an addressed item can be reopened by the officer as not fixed). "Addressed" is set automatically when the linked section/document changes in a resubmission; "resolved" is set by the officer. | UC2 "Resolution of previously flagged issues is tracked" |
| FR-025 | A complete audit trail of status changes, submissions, feedback and resolution events is stored and visible to officers. | UC2 Quality Assurance |
| FR-026 | Operators never see internal approval stages; they see only the mapped labels and the final outcome Approved/Rejected. | UC3 Constraints, UC2 Status Mapping |
| FR-027 | Officers can move an application through site-visit and approval states (Site Visit Scheduled, Site Visit Done, Pending Approval, Approved, Rejected) so the lifecycle completes. In v0.3.0 checklist capture (UC3) was deferred and Site Visit Done led straight to Pending Approval; from v0.4.0 (US-079, US-063) the checklist is the visit record and that direct route goes. | UC2 mapping table; UC3 |
| FR-028 | Users authenticate with email and password; three roles exist: operator, officer and admin. Each role lands on its own home screen. | Roles implied by the brief; admin is a product decision |
| FR-029 | An admin sees an operations dashboard: application counts by internal status, applications idle for more than 7 days, submissions/resubmissions today, AI verification health (runs in 24 h, failure rate, average latency, provider), and a cross-application audit feed. | Not in the brief; product decision (SCOPE.md) |
| FR-030 | An admin can open any application read-only (officer view, no actions) and manage users: list users, change a user's role, deactivate and reactivate a user. Accounts are created by script, not in the app (amended 19 and 20 Sep 2026). Every user change is an audit event. The last active admin cannot be demoted or deactivated; the seeded demonstration accounts are protected; an admin cannot change their own account. Operators and officers receive 403 on admin endpoints. | Not in the brief; product decision |
| FR-031 | A public landing page explains the service (how it works, what documents are needed, accepted formats, status tracking) and links to sign-in. | Engineering assumption; UX |
| FR-035 | Approval issues a licence certificate (PDF) in the same transaction; the officer can preview it before deciding; the operator and officers can download it afterwards. | Product decision (US-051, 19 Sep); not in the brief |
| FR-036 | Once a site visit is scheduled the officer can open the inspection checklist for that visit: seventeen items in five sections from a versioned template, each with a result (satisfactory, unsatisfactory, not applicable), a comment and a "Need further clarification" flag. One checklist per visit; a second visit gets its own. (v0.4.0) | UC3 "Officer accesses the full checklist after site visit is scheduled", "inputs comments per checklist item" |
| FR-037 | The checklist's findings freeze when it is submitted; the clarification state of each item keeps changing through the rounds. (v0.4.0) | UC3; engineering assumption |
| FR-038 | The checklist saves as a draft while the officer works, on a tablet and over a poor connection: idempotent saves, a visible saved or retrying state, an offline notice, and a merge instead of a silent overwrite when another session saved. (v0.4.0) | UC3 "save as draft (e.g. while working on an iPad on-site)" |
| FR-039 | An item flagged "Need further clarification" or marked unsatisfactory needs a comment; the operator reads the comment of a flagged item. (v0.4.0) | UC3 "mark individual items as Need Further Clarification" |
| FR-040 | Submitting the checklist moves the case to Awaiting Post-Site Clarification through the workflow table, releases the flagged items to the operator, audits both, and notifies the operator once. (v0.4.0) | UC3 "On checklist submission, case automatically moves to Pending Post-Site Clarification" |
| FR-041 | The operator sees only the flagged items with the officer's comment (the response model has no field for the rest of the checklist), answers each one with text and up to three supporting files under the document rules, and sends the answers as one round. (v0.4.0) | UC3 "Operator does NOT see the full checklist", "sees ONLY the items flagged", "can respond to each item and upload supporting documents" |
| FR-042 | The officer marks an answered item clarified or asks again; rounds are unlimited and counted per item; every request, response, attachment and decision is on the item's own trail with timestamps. Reject and Withdraw remain possible from every post-site state. (v0.4.0) | UC3 "Multiple clarification rounds are supported per checklist item", "Each item maintains a full audit trail" |
| FR-043 | The site visit is arranged inside the case: the officer proposes a date and slot, the operator accepts or proposes another date with a reason, the officer accepts, keeps or proposes again, either side can reschedule before the date, the officer can confirm after three working days of silence (never later than the visit date), at most six proposals are made per visit (then only accept or keep remain), and the visit is marked done only once confirmed. (v0.4.0, US-084, built 20 Sep 2026) | Not in the brief; owner's product decision (20 Sep 2026) |
| FR-034 | An operator can delete a draft that was never submitted; it is removed outright with its files and audit events. Submitted applications are never deleted. | Product decision (US-045, 19 Sep) |
| FR-033 | An officer can resolve only feedback the operator has seen; an unsent item can only be withdrawn. An officer can undo their own withdraw or resolve within a short grace window; the undo is audited. | Product decision (US-039, 19 Sep) |
| FR-032 | An operator can withdraw a submitted application at any point before a decision, with an optional reason. Withdrawn is terminal, officers are notified, and the change is audited with the operator as actor. Drafts are not withdrawn (they are simply left). | Product decision (US-038, 19 Sep); not in the brief |

## 2. Non-functional requirements

| ID | Requirement |
|----|-------------|
| NFR-001 | The system runs locally from the README with Docker Compose (Postgres) plus two dev servers, on a clean machine. (SUB) |
| NFR-002 | API responses for list/detail endpoints complete in under 500 ms at MVP data volumes; AI verification is asynchronous so uploads return immediately. |
| NFR-003 | The codebase is a modular monolith with clear module boundaries (see `docs/03-architecture/ARCHITECTURE.md`). (EVAL code quality) |
| NFR-004 | TypeScript strict mode, no `any`; Python typed with mypy-clean core modules; linting enforced in CI. |
| NFR-005 | Configuration is via environment variables with documented defaults; no secrets in the repository. (SUB) |
| NFR-006 | The application is deployable to Railway (backend + Postgres + static frontend) with a health endpoint. |
| NFR-007 | Structured logs include request id, user id (when authenticated), route, status and duration; AI calls log latency and outcome. |
| NFR-008 | Checklist draft saves answer in under 300 ms at p95 at MVP volume (a save is one document of at most 32 KB: seventeen items, comments of at most 2,000 characters); the client sends one save per pause of 1.5 s, never one per keystroke. (v0.4.0, US-086) |
| NFR-009 | Attachment limits: one file at most 10 MB (the document rule), three files per clarification response, and a storage budget of 150 MB per application across documents, licence and attachments, refused with 422 `storage_budget` and a sentence the operator can act on. Images (JPG, PNG) are stored as uploaded; no server-side downscaling in v0.4.0. (v0.4.0, US-085) |
| NFR-010 | Uploaded images carry no metadata: EXIF (GPS, device, timestamps) is stripped on the server before the file is stored, since an officer downloads what a phone camera wrote. (v0.4.0, US-085) |
| NFR-011 | Admin read endpoints answer in under 500 ms at p95 with 10,000 applications and 100,000 audit rows (indexes on `audit_events (application_id, created_at)` and `verification_runs (started_at)`; the activity feed by keyset, never `OFFSET`). (v0.4.0, US-086) |
| NFR-012 | Poor connections: a failed checklist save or attachment upload retries with backoff (1 s, 2 s, 4 s, up to 30 s); the offline notice appears within a second of the browser reporting `offline`; nothing typed is lost while the tab stays open. (v0.4.0, US-087) |
| NFR-013 | Phone performance for the operator's respond page: first contentful paint under 2.5 s on a throttled 4G profile; the page's JavaScript under 250 KB gzipped; uploads show progress. (v0.4.0, US-087) |
| NFR-014 | Storage is observed: a `permitflow_storage_bytes` gauge by kind (documents, licences, attachments) on `/metrics`, an alert at 80 % of the Railway volume, and the volume size written in `OPERATIONS.md`. (v0.4.0, US-089) |
| NFR-015 | The eight new screens pass the accessibility gate (WCAG 2.2 AA plus best practice, axe-core) in CI, every touch target on the checklist and the respond page is at least 44 px, and the checklist is workable by keyboard (Tab through the items, Space to pick a result). (v0.4.0, US-088) |
| NFR-016 | Every date the site visit, the checklist and the admin screens show is in Singapore time (Asia/Singapore) and stored in UTC; "today" and "idle" on the admin overview are Singapore calendar days. (v0.4.0, US-090) |
| NFR-017 | Use case 3 is observable: counters for checklists submitted, clarification rounds requested and attachment bytes stored, a dashboard row generated from the same script as the rest, and the post-site states in the Telegram `/queue` reply. (v0.4.0, US-089) |
| NFR-018 | Audit growth is bounded: no audit row per draft save; the activity feed is read in pages of 50 by keyset; the audit table's indexes carry the admin queries. (v0.4.0; covered by US-061, US-072, US-086) |

## 3. Security requirements

| ID | Requirement |
|----|-------------|
| SEC-001 | Every application-scoped endpoint enforces ownership (operator) or role (officer) on the server. Frontend hiding is never the only control. |
| SEC-002 | Operators cannot read, update or list applications they do not own; attempts return 404 (to avoid confirming existence). The repository logs at WARNING when a row exists but is owned by someone else, so IDOR attempts are distinguishable from bad ids in logs without revealing that to the caller. Sub-resources (documents, feedback, notifications) are additionally checked to belong to the parent application or user. |
| SEC-003 | Officer-only endpoints (status change, feedback, audit trail, queue) reject operators and admins with 403; admin-only endpoints reject operators and officers with 403. Amended for v0.4.0 (US-072): the officer's read endpoints (queue, case, audit trail, checklist, compare, downloads) also admit the admin, whose `actions[]` is empty by construction; every officer mutation, the feedback templates and the licence preview keep refusing the admin. |
| SEC-004 | Status transitions are validated server-side by the state machine; invalid transitions return 409 with a machine-readable error. |
| SEC-005 | Uploads are validated on the client and again on the server: extension and MIME allowlist (PDF, PNG, JPEG, TXT), magic-byte check, 10 MB streamed cap; files are stored with server-generated names outside the web root and served only through an authorized endpoint. A `sha256` is computed and stored per file: re-uploading a file identical to the current file of the same document type is reported as no change (and does not count as addressing feedback), and the hash is used for revision diffs. PDF is the recommended format; images are accepted but not machine-readable in the MVP. |
| SEC-006 | Passwords are hashed with argon2. JWT access tokens expire after 8 hours and are signed with `JWT_SECRET` from the environment; the application refuses to start without it in every environment; no fallback secret exists in the code. |
| SEC-007 | All inputs are validated with Pydantic (backend) and Zod (frontend). Database access uses the ORM with bound parameters only. |
| SEC-008 | Document text sent to the LLM is treated as untrusted data: it is delimited, the prompt instructs the model to ignore instructions within it, and the model output is validated against a strict schema before use. |
| SEC-009 | Audit events are append-only at the application layer (no update/delete endpoints or ORM methods). |
| SEC-010 | `/auth/login` is rate limited on failed attempts: 10 failures per minute per IP → 429; limits are configurable and disabled in the test environment. |
| SEC-011 | Security headers (CORS allowlist, no-sniff, frame denial) are set on API responses. |
| SEC-012 | Document text and form data sent to the LLM provider are limited to what verification needs (document type, extracted text capped at 20 000 characters, the matching form section); the provider, model and data-handling terms are documented; `extracted_text` is retained only while the application is open and deleted 90 days after a terminal state (production requirement; the MVP documents the gap). |

## 4. AI requirements

| ID | Requirement |
|----|-------------|
| AI-001 | Each uploaded document is text-extracted (PDF/TXT; images are recorded as "not extractable" in the MVP) and sent to an AI verifier with the document type and the relevant application form data. |
| AI-002 | The verifier returns a structured result: `status` (verified / issues_found / unreadable), `confidence` (0–1), `issues[]` (code, severity, message, evidence), `missing_information[]`, `summary`. |
| AI-003 | The raw model output is validated against a Pydantic schema. Invalid or partial output results in a `failed` verification with the reason recorded, never a crash or a fabricated result. |
| AI-004 | Deterministic post-processing applies business rules: confidence below `AI_CONFIDENCE_THRESHOLD` (default 0.6) downgrades `verified` to `needs_review`; the prompt-injection heuristic also forces `needs_review`; empty extracted text short-circuits to `unreadable` without calling the model. Issue codes come from a fixed `IssueCode` enum. |
| AI-005 | AI results are advisory. No AI output changes application status, feedback or any authoritative state. |
| AI-006 | If the AI provider is not configured, times out or errors, the document is marked `unavailable` and the application remains fully submittable and reviewable. |
| AI-007 | The AI provider sits behind a single interface; a deterministic mock provider is used in tests and when no API key is present. |
| AI-008 | A small evaluation set (valid, wrong document type, missing information, ambiguous, empty, prompt injection) exists with expected outcomes and can be run against the real provider. |
| AI-009 | The operator can re-trigger verification for a document after re-upload; each verification attempt is stored with timestamp and provider metadata. |

## 5. Auditability requirements

| ID | Requirement |
|----|-------------|
| AUD-001 | Every revision stores a full snapshot of form data and the set of document ids at submission time. |
| AUD-002 | Every status transition records from-state, to-state, actor, timestamp and optional note. |
| AUD-003 | Every feedback creation, resolution change and template use is recorded as an audit event. |
| AUD-004 | Every document upload, replacement and verification outcome is recorded as an audit event. |
| AUD-005 | Audit events are written in the same database transaction as the change they describe. |
| AUD-006 | The audit trail is readable by officers via the API and UI in chronological order. |
| AUD-007 | Every checklist and clarification event (created, submitted, requested, released, answered, attachment added, resolved, reopened, withdrawn) and every site visit appointment event is an audit row in the same transaction; a draft save of the checklist is not audited (the draft is not a record until submitted). (v0.4.0) |

## 6. UX requirements

| ID | Requirement |
|----|-------------|
| UX-001 | Visual direction: clean, light canvas, deep red accent, charcoal text, restrained semantic colours; enterprise licensing platform feel. No reuse of government branding. |
| UX-002 | Every data view has explicit loading, empty, error and success states. |
| UX-003 | Form validation errors appear inline next to fields and are announced on submit. |
| UX-004 | Feedback on the operator view is anchored: clicking a feedback item scrolls to and highlights its section or document. |
| UX-005 | Status is shown as a labelled badge using the role-specific label. |
| UX-006 | Officer diff view uses side-by-side or inline field comparison with changed fields visually marked. |
| UX-007 | Layouts work at 390 px, 1024 px and 1280 px widths without horizontal scroll (the design phase moved the checkpoints from 375/768 to the phone and tablet widths in `docs/04-design/`). |
| UX-008 | Interactive elements are keyboard reachable and have visible focus; colour is never the only signal. |

## 7. Reliability and error-handling requirements

| ID | Requirement |
|----|-------------|
| REL-001 | All API errors return a consistent JSON body `{ "error": { "code", "message", "details?" } }` with appropriate HTTP status. |
| REL-002 | Submission and resubmission are atomic: revision, status change, notifications and audit events commit together or not at all. |
| REL-003 | AI verification failures are isolated to the document record; they never fail the upload request or the submission. |
| REL-004 | AI calls have a timeout (30 s) and one retry on transient errors. |
| REL-005 | The frontend retries idempotent reads and shows a retry action on failure; mutations show a clear error and preserve user input. |
| REL-006 | A `/health` endpoint reports API and database status (503 when the database is unreachable); it does not expose provider configuration. |
| REL-007 | Every mutating service locks the application row for its transaction; officer status changes also carry an optimistic `expected_version` (409 `version_conflict` on a stale screen); operator submit/resubmit rely on the lock plus the state machine (409 `invalid_transition`). |
