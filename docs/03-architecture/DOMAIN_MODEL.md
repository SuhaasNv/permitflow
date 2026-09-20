# PermitFlow: Domain Model

Names below are the names to be used in code (`backend/app/models/`). Ownership rules are enforced in repositories and services (ADR-005).

## Entity overview

```
User 1───* Application 1───* ApplicationRevision
                 │                    │
                 │                    └── form_data (JSON snapshot) + document_ids
                 ├───* Document 1───* VerificationRun
                 ├───* Feedback  (targets a section_key or a document_type; raised_in_revision)
                 ├───* Notification (per user)
                 ├───* AuditEvent (append-only)
                 ├───1 Licence (one per approved application, US-051)
                 ├───* SiteVisit 1───* SiteVisitProposal (the appointment and its rounds, US-084)
                 └───* Checklist 1───* ChecklistItem 1───* ClarificationRequest 1───1 ClarificationResponse 1───* ClarificationAttachment
```

## Entities

### User
| Field | Type | Notes |
|-------|------|-------|
| id | UUID | |
| email | str, unique | login identifier |
| password_hash | str | argon2 |
| full_name | str | |
| role | enum `operator` \| `officer` \| `admin` | single role per user (assumption); admin is read-only on applications |
| is_active | bool | inactive users cannot authenticate; set by an admin (deactivate/reactivate); re-read on every request |
| is_protected | bool | the published demonstration accounts (US-073): no admin may change their role or deactivate them |
| created_at | datetime | |

Ownership: a user owns their notifications. Operators own the applications they create. Administrators (US-073, built 21 Sep 2026) change roles, deactivate and reactivate accounts and create them; `AdminUserService` locks every admin row (`SELECT ... FOR UPDATE ... ORDER BY id`) and refuses a change that would leave no active admin (`last_admin`), a change to the caller's own row (`self_change`, which wins) and a change to a protected account (`protected_account`); a deadlock between two administrators is 409 `try_again`. User changes are audit events with `application_id = null`: `user.created`, `user.role_changed` (from, to), `user.deactivated`, `user.reactivated`, beside the session events of US-093.

### UserSession (v0.4.0, US-093)
| Field | Type | Notes |
|-------|------|-------|
| id | UUID | the `sid` claim of the token issued at sign-in |
| user_id | UUID → User | indexed; a partial index on (user_id, expires_at) where `revoked_at IS NULL` serves the "is another session live?" read and the gauge |
| device_label | str(60) | "Safari on iPad", derived from the User-Agent at sign-in by `domain/device_label.py`; the header itself is never stored |
| last_seen_at | datetime | refreshed by authenticated requests, at most once a minute per session |
| expires_at | datetime | the token's own expiry |
| revoked_at | datetime, nullable | set once |
| revoked_reason | `taken_over` \| `signed_out` \| `idle`, nullable | why the row stopped being live |
| created_at | datetime | |

Live means: not revoked, `expires_at` in the future, `last_seen_at` within `SESSION_IDLE_MINUTES`. An account has at most one live session; `AuthService.authenticate` reads the live row under `FOR UPDATE`, refuses with `session_active` or, with `take_over`, revokes it (`taken_over`) and audits `user.session_taken_over` with `application_id = null`. Every authenticated request reads the row by id (`AuthService.current_user`); an idle row is closed the first time it is seen again. Sign-out revokes (`signed_out`) and audits `user.signed_out`.

### Application
The aggregate root. Holds current status and the editable working copy of form data.
| Field | Type | Notes |
|-------|------|-------|
| id | UUID | |
| reference_no | str, unique | human-readable, e.g. `PF-2026-000123` |
| operator_id | FK User | owner; must have role operator |
| licence_type | enum | only `food_establishment` in the MVP |
| status | enum `ApplicationStatus` | internal status; see STATE_MACHINE.md |
| draft_data | JSON | working copy edited by the operator between submissions; copied into a revision on submit |
| current_revision_id | FK ApplicationRevision, nullable | latest submitted revision |
| decision_note | text, nullable | officer note shown to the operator on approval/rejection |
| draft_data.declarations.confirmed_at | stamped string | set by the server when the declarations are saved while responding to feedback; the diff reports it as "Confirmed on" so a re-confirmation counts as the change (US-041 follow-up) |
| withdrawal_reason | text, nullable | operator's reason when they withdrew (US-038); served to officers and, once withdrawn, to the owner |
| version | int | optimistic concurrency token (REL-007) |
| created_at, updated_at | datetime | |

Rules:
- `draft_data` is editable only when status is `draft` (all sections) or `pending_pre_site_resubmission` (only sections/documents with open feedback).
- `status` changes only through `workflow.transition`.

### ApplicationRevision
Immutable snapshot created at each submission.
| Field | Type | Notes |
|-------|------|-------|
| id | UUID | |
| application_id | FK Application | |
| revision_number | int | 1, 2, 3 …; unique per application |
| form_data | JSON | full snapshot of all sections |
| document_ids | JSON list[UUID] | the current document per type at submission time |
| submitted_by | FK User | |
| submitted_at | datetime | |

Rules: never updated or deleted. Diff between two revisions is a pure function (`domain/diff.py`).

### Document
An uploaded file for one document type. Replacement creates a new row that supersedes the old one, so historical revisions keep their references.
| Field | Type | Notes |
|-------|------|-------|
| id | UUID | |
| application_id | FK Application | |
| document_type | enum `DocumentType` | `business_profile`, `floor_plan`, `tenancy_agreement`, `food_hygiene_certificate`: one current document per type; no free-form `other` slot in the MVP (multi-file slots would need per-id feedback targets, deferred) |
| original_filename | str | sanitised for display only |
| stored_key | str | storage key generated by the server (never the client name) |
| content_type | str | allowlisted |
| size_bytes | int | ≤ 10 MB |
| sha256 | str | integrity, duplicate detection (identical re-upload for the same type is reported as no change) and revision diff; for JPG and PNG the digest and size are those of the stored bytes, re-written without metadata (US-085) |
| extracted_text | text, nullable | first 20 000 characters; null if not extractable |
| supersedes_id | FK Document, nullable | previous document of the same type |
| is_current | bool | exactly one current document per (application, type) |
| uploaded_by | FK User | |
| uploaded_at | datetime | |

### VerificationRun
One AI verification attempt for a document. The latest run is the document's displayed verification.
| Field | Type | Notes |
|-------|------|-------|
| id | UUID | |
| document_id | FK Document | |
| status | enum `VerificationStatus` | `pending`, `running`, `verified`, `issues_found`, `needs_review`, `unreadable`, `failed`, `unavailable` |
| provider | str | `openai`, `mock`, `none` |
| model | str, nullable | |
| confidence | float, nullable | 0–1 as reported by the model |
| summary | text, nullable | one-paragraph explanation |
| issues | JSON list | `{code, severity, message, evidence}` |
| missing_information | JSON list[str] | |
| error_reason | str, nullable | for `failed`/`unavailable`/`unreadable` |
| raw_output_valid | bool, nullable | whether provider output passed schema validation |
| started_at, finished_at | datetime | |
| latency_ms | int, nullable | |

Rules: results are advisory. No service reads verification status to decide workflow state (ADR-006).

Verification status vocabulary (who sets it, when):

| Status | Set by | When |
|--------|--------|------|
| `pending` | upload service | run row created; task not started |
| `running` | task | task picked up the run |
| `unreadable` | rule (no model call) | no extractable text (image, empty or encrypted PDF, unsupported type) |
| `verified` | model + rules | model reports `verified`, confidence ≥ threshold, no injection flag |
| `issues_found` | model | model reports one or more issues (see codes) |
| `needs_review` | rule | model reported `verified` but confidence < `AI_CONFIDENCE_THRESHOLD` (default 0.6), or the injection heuristic fired (a document that tries to instruct the model is never shown as `verified`) |
| `failed` | task | provider returned output that failed schema validation (`raw_output_valid = false`), or raised a non-transient error |
| `unavailable` | task | no provider configured, or timeout/network error after one retry |

Issue codes (`IssueCode` enum, used in the provider output schema and the UI): `wrong_document_type`, `missing_field`, `field_mismatch` (document contradicts the form, e.g. business name), `expired_document`, `illegible_content`, `possible_prompt_injection`, `other`. Severity: `low`, `medium`, `high`. Confidence is the model's self-report and is uncalibrated; it is shown to officers as a hint, never used for decisions.

### Feedback
An officer's contextual comment tied to a form section or a document type, raised in a specific revision, with a resolution lifecycle.
| Field | Type | Notes |
|-------|------|-------|
| id | UUID | |
| application_id | FK Application | |
| raised_in_revision_id | FK ApplicationRevision | the revision the officer was reviewing |
| author_id | FK User | officer |
| target_type | enum `section` \| `document` | |
| section_key | str, nullable | e.g. `premises` when target_type = section |
| document_type | enum, nullable | when target_type = document (stable across replacements; the target is the slot, not a file id) |
| released_to_operator_at | datetime, nullable | set when the officer requests resubmission; operators see only released items |
| template_key | str, nullable | which comment template was used, if any |
| message | text | |
| resolution | enum `open` \| `addressed` \| `resolved` \| `withdrawn` | |
| previous_resolution | enum, nullable | resolution before the last withdraw, resolve or reopen, cleared on undo (US-039) |
| addressed_in_revision_id | FK ApplicationRevision, nullable | set automatically on resubmission when the target changed |
| resolved_by | FK User, nullable | officer |
| resolved_at | datetime, nullable | |
| created_at | datetime | |

Lifecycle: `open` → `addressed` (system, on resubmission when the target changed: section compared by value, document by `sha256`) → `resolved` (officer). Officer may `withdraw` an open item, or mark an addressed item as not fixed (`addressed` → `open`, audited `feedback.reopened`, US-049; the item leaves the operator's view until the next request for resubmission releases it again). Create, withdraw and reopen are allowed only while the application is `under_review` (see STATE_MACHINE.md, feedback lifecycle rules).

### Notification
| Field | Type | Notes |
|-------|------|-------|
| id | UUID | |
| user_id | FK User | recipient |
| application_id | FK Application | |
| kind | enum | `submitted` (to all officers), `resubmitted` (to all officers), `status_changed` (to the operator): there is no officer assignment model, so "officers" means every active officer user |
| title, body | str | |
| read_at | datetime, nullable | |
| created_at | datetime | |

Email delivery is mocked: an `EmailNotifier` logs the message.

### AuditEvent
Append-only.
| Field | Type | Notes |
|-------|------|-------|
| id | UUID | |
| application_id | FK Application, nullable | null for user-management events |
| actor_id | FK User, nullable | null for system events |
| event_type | str | `application.created`, `section.updated`, `document.uploaded`, `document.replaced`, `document.deleted`, `verification.requested`, `verification.completed`, `revision.submitted`, `status.changed`, `feedback.created`, `feedback.released`, `feedback.addressed`, `feedback.resolved`, `feedback.withdrawn`, `feedback.reopened`, `feedback.restored`, `licence.issued` (planned with the admin epic: `user.role_changed`, `user.deactivated`, `user.reactivated`) |
| payload | JSON | event-specific data (from/to status, revision number, feedback id, document type, verification status) |
| created_at | datetime | |

### Licence

The certificate issued by the approval transaction (US-051, ADR-010): one row per approved application, rendered to a PDF on the uploads volume and served through `GET /applications/{id}/licence` (owner or officer).

| Field | Type | Notes |
|-------|------|-------|
| id | UUID | |
| application_id | FK Application, unique | |
| licence_no | str, unique | `FEL-<year>-<n>`, `n` from the sequence `licence_no_seq`; the year is the Singapore calendar year of issue |
| revision_number | int | the revision the licence was issued against |
| issued_by | FK User | the approving officer |
| issued_at | datetime | |
| valid_from, valid_to | date | Singapore calendar dates, one year |
| verification_code | str | printed on the certificate for a future public verification page |
| stored_key | str | server-generated key of the PDF |
| sha256 | str | of the rendered PDF |

### SiteVisit

The appointment for the on-site inspection (US-084, FR-043). No new application status: it lives inside `site_visit_scheduled`, one row per visit number (`visit_no` 1 today; a second visit is not reachable through the workflow in v0.4.0). Every change is written with its audit row and notification in the same transaction.

| Field | Type | Notes |
|-------|------|-------|
| id | UUID | |
| application_id | FK Application | unique with `visit_no` |
| visit_no | int | 1-based per application |
| status | enum `proposed`, `counter_proposed`, `confirmed`, `done` | `done` is set by the `site_visit_done` transition |
| date | date | the date on the table (the officer's proposal, or the confirmed date while the operator asks to move it) |
| slot | enum `morning` (09:00 to 12:00), `afternoon` (14:00 to 17:00) | Singapore time |
| note | text, max 500 | the officer's note to the operator (what to have ready) |
| proposed_by_id, confirmed_by_id | FK User, nullable | |
| confirmed_at, done_at | datetime, nullable | |
| created_at, updated_at | datetime | |

Rules (`domain/site_visit.py`, pure): dates are Singapore calendar days, Monday to Friday (no public-holiday calendar, SCOPE assumption); the officer proposes at least one working day ahead, the operator at least two; at most 60 days out; a proposal the operator leaves unanswered may be confirmed by the officer after three working days, never later than the visit date; at most six proposals per visit (both sides together, reschedules included), after which only accept or keep remain.

### SiteVisitProposal

One row per round of the negotiation: the officer's proposal, the operator's counter, the officer's third date, either side's reschedule request.

| Field | Type | Notes |
|-------|------|-------|
| id | UUID | |
| site_visit_id | FK SiteVisit | |
| round_no | int | 1-based per visit, gap-free |
| author_id | FK User | |
| author_role | `officer` or `operator` | the operator view shows "Licensing officer" for officer rounds, never the name |
| date, slot | | |
| reason | text, max 500, nullable | required for a counter and a reschedule |
| outcome | enum `pending`, `accepted`, `kept`, `declined`, `superseded` | set once, when the round is decided; earlier rounds keep their outcome after a reschedule |
| created_at, decided_at | datetime | |

### Checklist

The inspection record of one visit (US-060, FR-036, FR-037). Created on the officer's first open while the case is `site_visit_scheduled` or `site_visit_done`, under the application row lock; one per (application, visit number); the current one is the highest visit number. A draft until submitted (US-063).

| Field | Type | Notes |
|-------|------|-------|
| id | UUID | |
| application_id | FK Application | unique with `visit_no` |
| visit_no | int | the current SiteVisit's number when one exists, else the next on record |
| schema_version | int | the template version the items follow (1) |
| status | enum `draft`, `submitted` | |
| version | int | optimistic token for the draft save; every save bumps it |
| last_save_id | str, nullable | the last accepted client save id: a replayed save answers with the current state |
| created_by_id, submitted_by_id | FK User | |
| created_at, updated_at, submitted_at | datetime | |

### ChecklistItem

One template item on one checklist; every key of the template is present from creation.

| Field | Type | Notes |
|-------|------|-------|
| id | UUID | |
| checklist_id | FK Checklist | unique with `item_key` |
| item_key, position | str, int | from `domain/checklist_schema.py` |
| result | enum `not_assessed`, `satisfactory`, `unsatisfactory`, `not_applicable` | `not_assessed` only while a draft |
| comment | text, max 2000, nullable | required at submit for an unsatisfactory or flagged item |
| needs_clarification | bool | the flag the operator will be asked about (US-062) |
| clarification_status | enum `none`, `open`, `answered`, `resolved`, `withdrawn` | restates the latest request's state; keeps changing after submit (US-064 to US-066) |
| resolved_by_id, resolved_at | | |

The template (`GET /checklist-schema`) is static in code and versioned like the form schema: seventeen items in five sections (Premises, Kitchen, Storage, Upkeep, People), each with a key, a title, one line of guidance and `applicable_by_default`. It follows the Singapore Food Agency's public Food Shop pre-licensing self-checklist and says in its own description that it is not an SFA document.

### ClarificationRequest

The officer's question on one flagged item, one row per round (US-063 to US-066). Round 1 is created and released when the checklist is submitted, with the officer's comment as its message; later rounds come from "Still needs clarification" and are released by "Request another round".

| Field | Type | Notes |
|-------|------|-------|
| id | UUID | |
| item_id | FK ChecklistItem | |
| round_no | int | 1 at submit, then increments per item |
| author_id | FK User | the officer |
| message | text, max 2000 | |
| released_at | datetime, nullable | the operator sees the request only once released |
| withdrawn_at | datetime, nullable | |
| created_at | datetime | |

### ClarificationResponse

The operator's answer to one request (US-065): one per request (unique), drafted then sent with the round; `message` up to 2000 characters; `sent_at` set by "Send responses"; append-only afterwards.

### ClarificationAttachment

Evidence on an answer (US-065): `original_filename`, `stored_key` (server-generated), `content_type`, `size_bytes`, `sha256`, `uploaded_by`, `uploaded_at`; the same allowlist, magic-byte and size checks as documents; at most three per answer; an identical file on the same answer is kept once; removable until the answer is sent. Both uploads share one pipeline (`services/uploads.py`): images re-written without metadata by `infra/images.py`, and the application's storage budget (`STORAGE_BUDGET_BYTES`, every document version plus evidence plus the licence, summed by the repositories) checked before the key is written (US-085).

### CommentTemplate (static configuration, not a table)
`{key, target_type, title, body}` defined in `domain/feedback_templates.py` and served by `GET /officer/feedback-templates` (officers only). Templates are data, not code, so they can move to a table later without API change.

## Form definition (Food Establishment Licence)

Defined once in `backend/app/domain/form_schema.py` and served at `GET /form-schema`; the frontend builds Zod validators from it.

| Section key | Fields |
|-------------|--------|
| `business` | business_name (text, required, ≤120), uen (text, required, pattern `^[0-9]{8,9}[A-Z]$`), entity_type (select: sole_proprietorship, partnership, private_limited, other), contact_name (text, required), contact_email (email, required), contact_phone (text, required, 8–15 digits) |
| `premises` | address_line_1 (text, required, ≤200), postal_code (text, required, 6 digits), premises_type (select: shophouse, mall_unit, hawker_stall, standalone), floor_area_sqm (number, required, 1–10000), tenancy_expiry (date, required) |
| `operations` | cuisine_description (textarea, required, ≤1000), seating_capacity (integer, required, 0–2000), operating_hours (text, required, ≤100), food_handlers_count (integer, required, 0–500) |
| `declarations` | information_accurate (checkbox, must be true), consent_to_inspection (checkbox, must be true) |

Required document types: `business_profile`, `floor_plan`, `tenancy_agreement`, `food_hygiene_certificate`. No optional slot in the MVP; a document in a `draft` application can be deleted by the operator (`document.deleted`), and in `pending_pre_site_resubmission` only flagged types can be replaced.

## Ownership and access summary

| Entity | Operator | Officer | Admin |
|--------|----------|---------|-------|
| Application | own only; read, edit draft/flagged, submit/resubmit | all; read, change status, decision note | all; read only |
| ApplicationRevision | own only; read | all; read, compare | all; read, compare |
| Document | own only; upload/replace when editable, download | all; download | all; download |
| VerificationRun | own documents; read, re-run | all; read, re-run | all; read; aggregate health metrics |
| Feedback | own applications; read | all; create, resolve, withdraw | all; read |
| Notification | own | own | own |
| AuditEvent | none | all applications; read | all applications; read, cross-application feed |
| SiteVisit, SiteVisitProposal | own application; accept, counter, reschedule | all; propose, decide, confirm, reschedule | all; read |
| Checklist, ChecklistItem | none (the operator receives the flagged items through the clarification view, US-064) | all; create, save, submit | all; read |
| ClarificationRequest, ClarificationResponse, ClarificationAttachment | own application; read released requests, draft and send answers, attach and remove files until sent, download own files | all; ask, resolve, withdraw (US-066); download | all; read, download |
| User | self | self | all; change role, deactivate/reactivate (planned, US-073) |

## Invariants (enforced in services and tested)

1. Exactly one current document per (application, document_type).
2. `revision_number` is strictly increasing and gap-free per application.
3. A revision's `form_data` and `document_ids` never change after insert.
4. On resubmission, sections and document types without open feedback are identical to the previous revision (sections compared by value, documents by `sha256`).
5. Status changes only via the workflow module and always produce a `status.changed` audit event.
6. Every mutating service writes its audit event(s) in the same transaction.
7. Operator API responses never contain internal status codes or audit events; they contain the operator label. (The appointment's own state names, `proposed` to `done`, are served to both sides with a role-specific label; they are not application statuses.)
8. `site_visit_done` is reachable only while the current visit is `confirmed`; the transition marks it `done` in the same transaction.
9. A visit has at most six proposals; a proposal's `outcome` is written once.
10. One checklist per (application, visit number); every template key is present from creation; `result`, `comment` and `needs_clarification` never change after `submitted_at`.
11. Indexes for the admin reads at volume (migration 0013, US-086): `audit_events (application_id, created_at)`, `(created_at, id)`, `(event_type, created_at)`; `verification_runs (created_at)` and `(started_at)`.
12. At most one live session per user; a token whose session is revoked, idle or missing never authenticates, whatever its `exp`.
