# PermitFlow: Release plan for v0.4.0

Status: proposed on 20 September 2026 (Sunday), revised the same evening after three independent reviews (an adversarial feasibility review, a product-design review, a QA and security review; section 12 lists what each changed), adopted by the owner the same evening with every recommendation of section 11. Nothing in this plan is built yet; `SPRINTS.md`, `USER_STORIES.md`, `SCOPE.md` and the Notion board carry it from 20 Sep, and Sprint 4 starts on the owner's go.

## 1. Goal and ground rules

**v0.4.0 in one line:** the two epics the Sprint 3 close deferred, built the way the first three sprints were built: use case 3, the site-visit checklist with targeted post-site clarification (UC3, US-060 to US-066), first; then the admin panel (E4, US-070 to US-073).

**Where the work lives.** Every story branches from `dev` and merges into `dev` with `--no-ff`; each merge deploys the development environment (https://dev.permitflow.space) automatically. Production (https://permitflow.space) stays on the submitted release, `sha-714a159` (v0.3.0 plus the 20 Sep fixes), and its one example application (PF-2026-001000) is not touched. Production changes only through the release ritual in section 9, and only when the owner says so.

**The reviewable artefact.** The GitHub default branch was `dev` until 20 Sep 2026, so a reviewer who opened the repository during the review window would have landed on the branch this plan rewrites story by story. Done and to do before the first v0.4.0 merge: (1) the default branch is `main`, where the submitted release lives (`gh repo edit --default-branch main`, run on 20 Sep at the owner's request); (2) put a two-line notice at the top of `README.md` on `dev` only: "This branch carries work toward v0.4.0. The submitted release is tag v0.3.0 on `main`, live at permitflow.space."; (3) leave the submitted sections of `AI_USAGE.md` untouched until after the debrief and add v0.4.0 as an appendix; (4) set the working version to `0.4.0-dev` (`frontend/package.json`) and `0.4.0.dev0` (`backend/pyproject.toml`) so the development footer says what it is, bumped to `0.4.0` at the release (`BRANCHING.md` rule 5, amended to `v0.<release>.0`).

**Why production is frozen.** If asked in the debrief why production was not updated: "Production is the version I submitted; v0.4.0 is being built on `dev` and deployed to the development environment on every merge; the board, `CHANGELOG.md` and `RELEASE_NOTES.md` show what is in progress, and the release is one pull request, one tag and one pinned image away."

**What does not change.** The standing rules of `CLAUDE.md`: every story carries its tests, its docs, its Notion status and its `--no-ff` merge; the sprint close ritual runs at the end of each sprint; nothing is pushed without a yes; no secrets through any tool; no em dashes, emoji or KPI card grids in anything new.

## 2. Scope

### MUST (the release is not v0.4.0 without these)

| # | Feature | Stories | Brief reference |
|---|---------|---------|-----------------|
| V1 | Officer opens the inspection checklist once the site visit is scheduled, records a result and a comment per item, saves it as a draft between rooms (tablet first, portrait and landscape) and submits it; a submitted checklist is immutable in its findings; one checklist per visit | US-060, US-061 | UC3 on-site data capture |
| V2 | Officer marks individual items "Need further clarification" with a comment the operator will read | US-062 | UC3 on-site data capture |
| V3 | Submitting the checklist moves the case to Awaiting Post-Site Clarification on its own, through the workflow table, audited and notified, and releases the flagged items to the operator in the same transaction | US-063 | UC3 status transition |
| V4 | Operator sees only the flagged items with the officer's comment per item; the operator response model has no field for the rest of the checklist, so the rule holds by construction, like the status codes (ADR-005) | US-064 | UC3 targeted response |
| V5 | Operator responds to each flagged item and attaches supporting documents (allowlist, magic bytes, 10 MB, server keys, authorised download), then sends the responses as one round | US-065 | UC3 targeted response |
| V6 | Several clarification rounds per item; the officer marks an item clarified or asks again; every request, response, attachment and decision is on the item's own trail with timestamps and in the audit trail | US-066 | UC3 multi-round clarification |
| V11 | The state machine carries the clarification guards, drops the checklist bypass, allows Reject from the three post-site states, and the workflow service takes an actor and a notification policy instead of assuming an officer; the sweep and `STATE_MACHINE.md` stay in step | US-079 | UC2 "no applications lost" |
| V12 | Tests per layer for every story, the new Playwright scenarios, the accessibility gate over the new screen states, `uat_edges.py` extended, coverage thresholds kept | every story | production readiness |
| V13 | Documents that describe what exists (section 8) | every story, US-080 | submission checklist |
| V17 | The per-client limiter keys on the real caller behind the Railway edge (readiness row 25), before the checklist's autosave lands on `dev`, so a tablet session cannot refuse every other visitor | US-082 | readiness row 25 |
| V24 | The site visit is arranged inside the case: the officer proposes a date and slot, the operator accepts or counters with a reason, the officer decides, either side can reschedule before the date, the officer can confirm after three working days of silence, and the visit is marked done only once confirmed; every round on record (owner's product decision, 20 Sep) | US-084 | beyond the brief (the brief has the status only) |

### Non-functional requirements (added 20 Sep 2026 at the owner's request: controlled development, not only features)

Each has a number in `REQUIREMENTS.md` (NFR-008 to NFR-018), a story with a measurable acceptance criterion and a sprint. None is optional except US-089.

| Story | Concern | Budget or rule | Sprint |
|-------|---------|----------------|--------|
| US-085 | Attachment limits, storage, image metadata | 3 files per response, 10 MB each, 150 MB per application; EXIF stripped on upload | 6 |
| US-086 | Latency under load | checklist save p95 300 ms, admin overview 500 ms, activity feed 200 ms at 10,000 applications and 100,000 audit rows; k6 script committed | 8 |
| US-087 | Poor connections and phone performance | retry with backoff, offline notice within 1 s, nothing lost while the tab is open; respond page under 250 KB gzipped JavaScript, first paint under 2.5 s on throttled 4G | 6 |
| US-088 | Accessibility | axe gate over the eight new screens, 44 px targets, keyboard checklist | 7 |
| US-089 | Observability and storage | counters for checklists, rounds and attachment bytes; storage gauge; alert at 80 % of the volume; `/queue` post-site counts (was V16) | 7 |
| US-090 | Time zone | every new date in Singapore time, stored UTC, tests around midnight | 5 |

### COMMITTED, first in the cut order (the admin epic)

Committed to v0.4.0 by product decision; if time forces a cut it ships as v0.5.0 and the release notes say so. It runs after UC3 because UC3 is the brief's open question and because the admin's read-only case page must cover the clarification rail UC3 adds.

| # | Feature | Stories |
|---|---------|---------|
| V7 | Admin overview: applications by status (drafts as one aggregate row, marked not visible to officers), cases idle for more than 7 days, submissions and resubmissions today, document-check health over 24 hours (runs by outcome, failure rate, average and p95 latency, provider and model), runs today against the platform quota; "today" and "idle" on the Singapore calendar day | US-070 (absorbs US-071) |
| V8 | Admin activity feed (latest 50 audit events, keyset cursor to older ones) and read-only access to any case on its own route, every action removed, every mutation refused with 403 | US-072 |
| V9 | Admin user directory: list, change role, deactivate and reactivate; the last active admin cannot be demoted or deactivated (admin rows locked in id order); no self-change; seeded demonstration accounts are protected; every change an audit event; a deactivated user gets 401 on the next request | US-073 |
| V10 | Seeded admin account and a spare, unprotected officer account for the admin scenario, in every environment; admin lands on the overview; the placeholder page is gone | US-073 |

### SHOULD (only when the rows above are green)

| # | Feature | Cut to |
|---|---------|--------|
| V16 | Now US-089 (non-functional table above) | the `permitflow_applications{status}` gauge already carries the three states; the counters are dropped |
| V18 | Server-provided `phase`, `outcome` and `can_resolve` on the officer case response (readiness row 22); the minimal operator-side field is already part of US-064 | stays a readiness row |
| V23 | Inline image thumbnails and a filename row for PDFs in the clarification thread, so the officer does not download blind | filename rows only |

### Parked for v0.5.0 (named now so they are not discovered missing in the debrief)

Photo evidence per checklist item from the officer's camera (the reviewers' first request in any inspection app); reason chips that fill an item's comment; ten-second undo for Mark clarified and Withdraw (the pattern of US-039); a late flag after submit; **a vision check on the operator's clarification photos (US-091, decided 20 Sep 2026: "does this photo show what was asked", yes, no or unclear with a reason, a golden set of photos, image tokens counted in the quota, after EXIF stripping and a downscale)**; an offline mirror of the checklist draft replayed on reconnect; CSV export of the activity feed; officer assignment (SCOPE C2); a user's own password change (needed once admins create accounts in the app).

### Cut order for v0.4.0 if behind

The admin epic whole (endpoints included; `scripts/create_user.py` and the seed still add the accounts) → V23 → V16 → V18 → the design pass folded into the stories → the checklist template reduced from seventeen items to ten → one attachment per response → item results reduced to comment plus flag. Never cut: V1 to V6, V11, V12, V13, V17.

## 3. Sprints

One-day sprints, the same cadence as `SPRINTS.md`. Five sprints, four and a half to five working days, paced around the interview: every merge into `dev` is a complete story with its tests and docs. Stories not finished at a close stay In progress (never "Done mostly"); the plan says below what `dev` shows between sprints.

### Sprint 4: "Agree the shape" (design pass and the workflow)

**Goal:** the eight new screens exist as artboards with their states matrix before code; the state machine and the workflow service carry what UC3 and the admin need; the limiter is fixed so autosave cannot hurt other visitors.

| Story | Title (short) | Priority | Notes |
|-------|---------------|----------|-------|
| US-078 | Design pass for the v0.4.0 screens | MVP | half a day: artboards for S-18, S-19, S-30 (820 portrait and 1024), S-31, S-40, S-41, S-42, S-43; the full states matrix (loading, empty, error, success, 403, 404, 409) written into `UI_STATES.md` first; the components to reuse named per screen (section 4.9); dialog copy from section 4.10 |
| US-079 | State machine and workflow service amendments | MVP | new and replaced edges, guards, Reject rows, the bypass removed, `WorkflowService` and `OfficerViewService` take the actor from the caller, a notification policy per edge, the sweep's expected table regenerated, the four suites that used the bypass rewritten to submit an all-satisfactory checklist stub, `STATE_MACHINE.md` and the reconciliation list in section 8 |
| US-082 | Limiter keyed on the real caller behind the edge | MVP | header-position change plus a forged multi-hop test; readiness row 25 closes |
| chore | Default branch to `main`, README notice on `dev`, working version `0.4.0-dev` | MVP | owner action for the default branch |

**Exit criteria:** sprint DoD; the sweep green with the new table; `dev` behaves exactly as before for every pre-site journey (the six Playwright scenarios and the journey green); artboards reviewed by the owner.

### Sprint 5: "The officer inspects" (UC3, officer half, plus what the operator sees)

**Goal:** after a site visit is scheduled the officer opens the checklist on a tablet, works through the seventeen items with autosave, flags what needs clarification, submits (marking the visit done in the same step when needed), and the case moves on its own; the operator sees the flagged items with the officer's comments.

| Story | Title (short) | Priority | Notes |
|-------|---------------|----------|-------|
| US-060 | Checklist schema, model (one per visit), migration, `POST` to create, officer capture screen | MVP | 820 portrait and 1024 first, then 390 and 1280 |
| US-061 | Idempotent draft autosave with a version, saved and retrying states, offline banner, conflict merge | MVP | no audit row per save |
| US-062 | "Need further clarification" per item with a required comment | MVP | |
| US-063 | Submit: completeness guard, findings frozen, the transition (with the site-visit-done hop when submitted from `site_visit_scheduled`), release of the flagged items, audit, one notification | MVP | |
| US-064 | Operator view of the flagged items (read-only until US-065), the `clarification` block on the operator view, dashboard and list wording | MVP | |

**Between Sprint 5 and 6, `dev` shows:** the officer's whole capture and submit; the operator sees the flagged items and the officer's comments with "Answering arrives with the next update" in place of the response fields; the officer keeps every exit (Route to approval when nothing is open, Reject, and the operator's Withdraw).

**Exit criteria:** sprint DoD; integration tests for create (201, 200, race), autosave (idempotent replay, conflict merge), submit from the wrong state, edit of findings after submit (409), submit with an unassessed item (422 with keys), submit with a flagged item without a comment (422), the transition with its audit order and single notification; the second-visit walk (approve path, Return to review, second visit, second checklist); `DOMAIN_MODEL.md`, `ARCHITECTURE.md`, ADR-013 written.

### Sprint 6: "The operator clarifies" (UC3, operator half)

**Goal:** the operator answers each flagged item with text and attachments, sends the round; the officer reviews the answers, marks items clarified or asks again, requests another round; a second round runs; the officer routes to approval and approves; the certificate is issued as before; the whole path is a Playwright scenario on a tablet viewport.

| Story | Title (short) | Priority | Notes |
|-------|---------------|----------|-------|
| US-065 | Responses with attachments (camera capture on phones); Send responses transition with its guard | MVP | reuses `domain/uploads.py`, `FileStorage`, `content_disposition()`; cap 3 files per response |
| US-066 | Rounds: Review responses, Mark clarified, Still needs clarification, Request another round, per-item trail (Timeline), operator history, notifications | MVP | |
| US-042 (extension) | Playwright `07-site-visit.spec.ts`; a11y gate over the checklist, respond and history states; `uat_edges.py` additions including the officer-only label check going live | MVP | |
| V23 | Thumbnails in the thread | Nice-to-have | only after the rows above are green |

**Exit criteria:** sprint DoD; `07-site-visit.spec.ts` green in CI; the five-round survival test; coverage thresholds held; `THREAT_MODEL.md` T24 to T26; `UI_STATES.md` as built.

### Sprint 7: "The office can see itself" (admin epic)

**Goal:** an admin signs in, sees whether anything is stuck and whether the checks are healthy, opens any case read-only (including a post-site case with its clarification rail), changes a role and deactivates an account, and every one of those is audited and tested.

| Story | Title (short) | Priority | Notes |
|-------|---------------|----------|-------|
| US-070 | Overview endpoint and page | MVP for the epic | reuses the status query of `services/metrics.py`; Singapore-day boundaries |
| US-072 | Activity feed and read-only case | MVP for the epic | the six code sites in section 5; `readOnly` hides item-level controls too |
| US-073 | User directory with protected accounts; seeded admin and spare officer | MVP for the epic | |
| US-042 (extension) | Playwright `08-admin.spec.ts` (restores the spare account at the end); a11y states for the four admin screens | MVP for the epic | |
| V16 | Observability additions | Nice-to-have | |

**Exit criteria:** sprint DoD; authorization matrix for every `/admin` route and every officer GET route (operator, officer, admin, anonymous); the two-admins concurrency test deterministic; `THREAT_MODEL.md` T19 as built; readiness row 15 updated.

### Sprint 8: "Release v0.4.0 honestly" (one full day)

**Goal:** UAT on the development environment, every document true, release notes written; the release itself is a checklist run on the owner's go, outside the sprint.

| Story | Title (short) | Priority |
|-------|---------------|----------|
| US-080 | UAT run U13 to U18 on development; readiness review, traceability, final review addendum, README, SCOPE, CHANGELOG, RELEASE_NOTES, docs index, `AI_USAGE.md` appendix | MVP |
| US-081 | Release v0.4.0 (section 9), on the owner's go, at any later date | release checklist |
| V18 | Readiness row 22 | Nice-to-have |

**Protected time:** once US-080 starts, no new features, only fixes and documents, as on Day 3.

## 4. Use case 3: design decisions (the content of ADR-013)

### 4.1 Reading of the three post-site statuses

The brief's grammar decides it. The officer label for `pending_post_site_resubmission` is "Awaiting Post-Site Resubmission": the officer waits for the operator. By the same grammar "Awaiting Post-Site Clarification" is the officer waiting for the operator's clarification, and the brief's UC3 goes straight from "On checklist submission, case automatically moves to Pending Post-Site Clarification" to "Operator sees ONLY the items flagged for clarification" with no officer release step in between. The first draft of this plan read `awaiting_post_site_clarification` as an officer working state to mirror `under_review`; the reviews showed the code encodes both readings at once (`workflow.py` labels "Request post-site resubmission" and "Request another round" on two edges that only make sense under different readings) and that the mirror costs the operator a turn with nothing to do and the officer an extra click per round. The plan now follows the brief's grammar:

| Internal status | Whose turn | Officer label (brief) | Operator label (brief) | Officer next action | Operator next action |
|-----------------|------------|-----------------------|------------------------|---------------------|----------------------|
| `site_visit_done` | officer (writing up) | Site Visit Done | Pending Post-Site Clarification | Submit checklist | none ("the officer is writing up the visit") |
| `awaiting_post_site_clarification` | operator, round 1 | Awaiting Post-Site Clarification | Pending Post-Site Clarification | Waiting on operator (or Route to approval when nothing is open) | Respond to clarification (n items) |
| `post_site_clarification_resubmitted` | officer | Post-Site Clarification Resubmitted | Post-Site Resubmitted | Review responses | none |
| `pending_post_site_resubmission` | operator, round 2 onwards | Awaiting Post-Site Resubmission | Pending Post-Site Resubmission | Waiting on operator | Respond to clarification (n items) |

Edges after US-079 (the sweep's expected table is regenerated from this list, never hand-edited):

| From | To | Actor | Guard | Label |
|------|----|-------|-------|-------|
| `site_visit_scheduled` | `site_visit_done` | officer | none | Mark site visit done (kept; also taken by the checklist submit when it runs from `site_visit_scheduled`, in the same transaction) |
| `site_visit_done` | `awaiting_post_site_clarification` | system (the checklist submit service) | checklist complete | Checklist submitted |
| `site_visit_done` | `pending_approval` | officer, transitional | `checklist_started = false` (Sprint 4: no checklist exists yet, so every pre-site journey still reaches approval); removed by US-063 with the four suite rewrites | the checklist becomes the visit record; SCOPE assumption 6 closes |
| `awaiting_post_site_clarification` | `post_site_clarification_resubmitted` | operator | `all_open_items_answered` | Send responses (new edge) |
| `awaiting_post_site_clarification` | `pending_approval` | officer | no `open` and no `answered` item | Route to approval (a checklist with nothing flagged, or everything withdrawn) |
| `awaiting_post_site_clarification` | `pending_post_site_resubmission` | removed | | an officer cannot re-request before the operator answers |
| `post_site_clarification_resubmitted` | `pending_post_site_resubmission` | officer | `open_clarification_count ≥ 1` | Request another round (replaces the edge back to `awaiting`) |
| `post_site_clarification_resubmitted` | `pending_approval` | officer | no `open` and no `answered` item | Route to approval |
| `pending_post_site_resubmission` | `post_site_clarification_resubmitted` | operator | `all_open_items_answered` | Send responses (existing) |
| the three post-site states | `rejected` | officer | `has_note` | Reject (new rows in `_REJECT_SOURCES`) |
| the three post-site states | `withdrawn` | operator | none | Withdraw (existing) |

`domain/officer_actions.py`: `awaiting_post_site_clarification` and `pending_post_site_resubmission` become "Waiting on operator" (`officer_turn = False`); `post_site_clarification_resubmitted` becomes "Review responses" (`True`); `site_visit_done` becomes "Submit checklist". `operator_view._needs_operator` derives from `officer_turn`, so the operator list shows Respond in both operator-turn states without further work; when nothing is open (a checklist with no flags) the row says "Waiting" because `clarification.can_respond` is false.

### 4.2 The checklist template

Static in code, versioned, served to the client, the way the form schema is (`domain/form_schema.py` → `domain/checklist_schema.py`, `GET /checklist-schema`, officers and admins). A configurable checklist is a form builder by another name and stays deferred with configurable forms.

The seventeen items follow the public Food Shop pre-licensing requirements of the Singapore Food Agency (section 2, design requirements, plus the maintenance and personnel rows of section 1: https://www.sfa.gov.sg/docs/default-source/default-document-library/self-checklist_foodshop.pdf). The template says so in its own description and does not claim to be an SFA document; the licence in this product is fictional.

| Section | Key | Item (title the officer sees) |
|---------|-----|-------------------------------|
| Premises | `layout_matches_plan` | Layout matches the submitted floor plan; kitchen area at least 10 m² excluding the servery |
| Premises | `floor_trap_graded` | Floor trap in the food preparation area; kitchen floor graded to it |
| Premises | `coved_edges` | Edge between wall and floor coved |
| Premises | `no_drain_hazards` | No manhole, inspection chamber, waste sump, grease trap or overhead waste pipe where food is prepared, stored or served |
| Premises | `walls_impervious` | Walls of the preparation and servery areas lined with impervious material to at least 1.5 m |
| Kitchen | `sink_provided` | At least one sink in the food preparation area, more for a large kitchen |
| Kitchen | `handwash_basin` | Wash-hand basin with soap for workers in the kitchen, separate taps if a double-bowl sink is used |
| Kitchen | `exhaust_air_cleaning` | Cooking fumes extracted at once, treated by an air-cleaning system and exhausted away from neighbours |
| Kitchen | `make_up_air` | Sufficient make-up air; negative pressure when the hood runs |
| Kitchen | `ducting` | Air ducts non-combustible, smooth, easy to clean, with inspection openings |
| Storage | `separate_storage` | Separate, pest-proof storage for personal belongings, cleaning materials, ingredients, cutlery and packaging |
| Storage | `chiller_temperature` | Temperature gauge on every refrigerator and chiller; chillers at or below 4 °C, freezers at or below minus 18 °C |
| Upkeep | `pest_control_contract` | Signed pest control contract covering rodents, cockroaches and flies, at least monthly |
| Upkeep | `cleaning_schedule` | Detailed cleaning schedule on the premises |
| Upkeep | `refuse_handling` | Covered refuse bins; refuse area clean and away from food areas |
| People | `food_handlers_certified` | Every food handler holds Food Safety Course Level 1 (refresher if attained more than five years ago) |
| People | `food_hygiene_officer` | Food Safety Course Level 3 holder appointed where the kitchen exceeds 16 m² or the shop spans two or more units (not applicable otherwise) |

Each item carries `key`, `section`, `title`, `guidance` (one line) and `applicable_by_default`. Result vocabulary per item: `satisfactory`, `unsatisfactory`, `not_applicable`, and `not_assessed` while the checklist is a draft. Rules: `unsatisfactory` requires a comment; `needs_clarification` requires a comment (the operator will read it); a submitted checklist has no `not_assessed` item. If the template must shrink (cut order), the ten kept are the five Premises rows, `handwash_basin`, `exhaust_air_cleaning`, `chiller_temperature`, `pest_control_contract` and `food_handlers_certified`.

### 4.3 Entities (additive; `DOMAIN_MODEL.md` gains these)

| Entity | Fields | Rules |
|--------|--------|-------|
| `Checklist` | id, application_id, visit_no (1, 2, …), schema_version, status `draft` \| `submitted`, version (optimistic token), created_by, created_at, updated_at, submitted_by, submitted_at | unique (application_id, visit_no); one per visit, so a case that returns to review and is scheduled again gets `visit_no + 1`; created by `POST` while the case is `site_visit_scheduled` or `site_visit_done` (201, or 200 with the existing draft; under the application row lock, so two tabs cannot create two); the current checklist is the highest `visit_no` |
| `ChecklistItem` | id, checklist_id, item_key, position, result, comment (nullable, ≤ 2000), needs_clarification (bool), clarification_status `none` \| `open` \| `answered` \| `resolved` \| `withdrawn`, resolved_by, resolved_at | unique (checklist_id, item_key); every key of the schema version present. **Column-level freeze at submit:** `result`, `comment`, `needs_clarification` never change after `submitted_at` (409 `checklist_submitted`); `clarification_status`, `resolved_by`, `resolved_at` keep changing through the rounds. `clarification_status` restates the latest request's state and is recomputed by the clarification service in the same transaction as the request or response that changed it |
| `ClarificationRequest` | id, item_id, round_no, author_id (officer), message (≤ 2000), created_at, released_at (nullable) | rounds are counted per item (`round_no` starts at 1 at checklist submit and increments on each "Still needs clarification"); there is no case-level round counter; at most one non-withdrawn request per item and round, enforced by the service under the application row lock (no database unique on the pair, so withdraw then ask again in a round cannot hit a constraint) |
| `ClarificationResponse` | id, request_id (unique), author_id (operator), message (≤ 2000), created_at, sent_at (nullable) | one per request; created while the case is in an operator-turn state; `sent_at` set by "Send responses"; append-only; the text of an unsent response is kept if the case ends first (section 4.6) |
| `ClarificationAttachment` | id, response_id, original_filename, stored_key, content_type, size_bytes, sha256, uploaded_by, uploaded_at | the same checks as documents (`domain/uploads.py`: name and type, magic bytes, 10 MB), the same `FileStorage` and `content_disposition()`; cap 3 per response (a constant), the fourth answers 422 `attachment_cap`; an identical file on the same response is "no change"; removable until sent (409 after), audited |

No new `ApplicationRevision` is created for a clarification round: the form data does not change, the checklist and the per-item threads are the record (assumption 19). The revision history and compare view keep showing the pre-site revisions.

### 4.4 Visibility by construction

`ChecklistOfficerView` (every item, results, comments, flags, threads) is returned only by officer and admin routes. `ClarificationOperatorView` is a different Pydantic model: a list of items that have at least one released request, each with the item title and guidance, the released requests, the operator's own responses and attachments, and the item's status in operator words (Waiting for your response, Sent, Clarified). It has no field for results, unflagged items or unreleased requests. The operator view of the application gains one block, `clarification: { can_respond, open_count, round }`, so the application page branches on a server fact instead of a label string (readiness row 22 is not made worse). Tests: flag 3 of 17 items and assert the operator receives exactly those 3 keys and no result value; an unreleased round-2 request stays invisible until "Request another round"; `uat_edges.py`'s officer-only label check goes live for the three post-site states and gains "Post-Site Clarification Resubmitted".

### 4.5 Services, guards, locks and side effects

`TransitionContext` gains `open_clarification_count`, `answered_clarification_count` and `all_open_items_answered`, built by `OfficerViewService.build()` and every mutating service from the same query. `WorkflowService.transition()` takes the actor from the caller (`actor_for_role(user.role)`, `Actor.SYSTEM` for the checklist submit) and consults a notification policy per edge (who is told, with which title and body); `OfficerViewService.build()` computes `actions[]` for the viewer's actor, so an admin receives an empty list. Every clarification mutation, the checklist create, save and submit, and "Send responses" lock the application row `FOR UPDATE` first, as every other mutating service does, and evaluate their guard after the lock: an item withdrawn a second before "Send responses" is excluded from `all_open_items_answered`, and a response cannot attach to a withdrawn item.

| Action | Where | Side effects (same transaction) |
|--------|-------|--------------------------------|
| Checklist create | `POST …/checklist` | row created with every item `not_assessed`; audit `checklist.created` (visit_no) |
| Draft save | `PUT …/checklist` with `version` and a client `save_id` | idempotent: a replayed `save_id` returns 200 with the current state; a stale `version` returns 409 with the current content so the client merges instead of reloading; no audit row per save |
| Submit | `POST …/checklist/submit` | from `site_visit_scheduled`: the officer hop to `site_visit_done` is recorded first (audit `status.changed`), then the system hop; findings frozen; round-1 requests created and released for flagged items (`open`); audit `checklist.submitted` (item counts, flagged keys) and `status.changed`; one operator notification with the count ("needs more information on 3 items", or "The site visit is recorded; nothing is needed from you" when none) |
| Respond | `POST …/responses`, attachments | operator-turn states only; audit `clarification.response_drafted` once per item, `clarification.attachment_added` |
| Send responses | `POST …/clarifications/send` | guard `all_open_items_answered` (422 listing unanswered keys); responses `sent_at`; items `answered`; audit `clarification.answered` per item and `status.changed`; every active officer notified |
| Mark clarified | officer, in `post_site_clarification_resubmitted` | `answered → resolved`; audit `clarification.resolved` |
| Still needs clarification | officer, same state | new unreleased request `round_no + 1`; `answered → open`; audit `clarification.reopened`; the rail shows "Not sent yet" until the round is requested |
| Withdraw | officer, `post_site_clarification_resubmitted` or `awaiting_post_site_clarification` | `open → withdrawn`; audit `clarification.withdrawn` |
| Request another round | officer transition | guard `open ≥ 1`; `released_at` on the new requests; audit `clarification.released` per item and `status.changed`; operator notified with the count |
| Route to approval | officer transition | guard: nothing `open` or `answered`; as today |

Notifications reuse the existing kinds (`status_changed` to the operator, `resubmitted` to officers) with new titles and bodies: `notifications.kind` is a 16-character column and new values would make the rollback in section 9 unsafe. The audit `event_type` column (48 characters) holds every new name.

### 4.6 Ends and edges

- Reject or Withdraw from a post-site state leaves the requests, responses and attachments as they are (the trail must show the true history); an unsent response stays visible to its author on the history page as "Draft, never sent"; the officer's rail shows the same.
- Return to review from `pending_approval` after a site visit, then a second visit: a new checklist with `visit_no = 2`; the operator's clarification view shows the current visit's items and the history page lists earlier visits.
- The seeded demonstration accounts (operator, officer, admin) carry `is_protected = true`; the admin endpoints refuse to change them (409 `protected_account`), which is what makes a published admin password acceptable in the demonstration (section 5).

### 4.7 API (all under `/api/v1`; every route in `ARCHITECTURE.md` with its roles and an authorization test)

| Method and path | Roles | Purpose |
|-----------------|-------|---------|
| `GET /checklist-schema` | officer, admin | the template, versioned |
| `POST /officer/applications/{id}/checklist` | officer | create the current visit's draft (201) or return it (200); 409 outside the site-visit states |
| `GET /officer/applications/{id}/checklist` | officer, admin | the current checklist; 404 until created; `?visit=n` for earlier visits |
| `PUT /officer/applications/{id}/checklist` | officer | idempotent draft save |
| `POST /officer/applications/{id}/checklist/submit` | officer | guards and the transition |
| `POST /officer/applications/{id}/clarifications/{item_id}/resolve` | officer | Mark clarified |
| `POST /officer/applications/{id}/clarifications/{item_id}/reopen` | officer | Still needs clarification, body: message |
| `POST /officer/applications/{id}/clarifications/{item_id}/withdraw` | officer | Withdraw |
| `POST /officer/applications/{id}/transition` | officer | existing endpoint; the new targets carry the guards above |
| `GET /applications/{id}/clarifications` | operator (owner) | `ClarificationOperatorView` |
| `POST /applications/{id}/clarifications/{item_id}/responses` | operator (owner) | one per released open request |
| `POST /applications/{id}/clarifications/responses/{response_id}/attachments` | operator (owner) | multipart, cap 3 |
| `DELETE /applications/{id}/clarifications/responses/{response_id}/attachments/{att_id}` | operator (owner) | until sent |
| `POST /applications/{id}/clarifications/send` | operator (owner) | the transition |
| `GET /applications/{id}/clarifications/attachments/{att_id}/download` and `GET /officer/applications/{id}/clarifications/attachments/{att_id}/download` | owner; officer, admin | the ownership chain (attachment → response → request → item → checklist → application → operator) is checked at every hop; an id from another application under this path is 404 |

Error bodies stay `{ "error": { "code", "message", "details"? } }`; operators never receive an internal status code.

### 4.7a Site visit appointment (US-084, added 20 Sep 2026 at the owner's request)

No new application status: the appointment is a record inside `site_visit_scheduled`, the way feedback items live inside `under_review`. `SiteVisit` (one per visit number, the number the checklist shares): date, slot (`morning` 09:00 to 12:00, `afternoon` 14:00 to 17:00), note, proposed_by, state `proposed` (waiting on the operator) | `counter_proposed` (waiting on the officer) | `confirmed` | `done`, plus `SiteVisitProposal` rows (round, author, date, slot, reason, outcome) as the history.

| Step | Who | Action | The other side |
|------|-----|--------|----------------|
| 1 | officer | Mark site visit scheduled collects date, slot and an optional note; `SiteVisit` created `proposed`; the case moves to `site_visit_scheduled` as today | notified with the date and slot; appointment card with Accept and Propose another date; the case sits under Needs your response |
| 2a | operator | Accept | `confirmed`; officer notified |
| 2b | operator | Propose another date: date, slot, a required one-line reason | `counter_proposed`; officer notified with the reason |
| 3 | officer | Accept the operator's date, Keep the original date, or Propose a third date | `confirmed` or `proposed` again; the operator is told which date stands and why |
| 4 | either | Reschedule a confirmed visit before its date, reason required | the same loop |
| 5 | officer | Confirm without a reply, available three working days after a proposal (the proposal notice says so) | `confirmed`; operator notified |
| 6 | officer | Mark site visit done: guarded by `visit_confirmed` | as today |

Rules (as built 20 Sep, ADR-013): Singapore working days (Monday to Friday, no holiday calendar), never in the past, within 60 days, officer proposals at least one working day ahead, operator proposals at least two (422 naming the rule); the reply deadline is three working days after the proposal and never later than the visit; at most six proposals per visit, both sides together, reschedules included, after which only accept or keep remain (owner's decision when asked how many loops there could be); the operator never cancels a visit (Withdraw remains); audit events `site_visit.proposed`, `site_visit.counter_proposed`, `site_visit.confirmed`, `site_visit.rescheduled` carry the dates; the checklist reads the confirmed date and slot. Left out for now: calendar sync (an .ics attachment is a v0.5.0 line), reminders by SMS, several officers.

API (notification kinds reused: `status_changed` to the operator, `resubmitted` to officers, the title carries the meaning; `notifications.kind` is `VARCHAR(16)`): `POST /officer/applications/{id}/site-visit` (propose, with the transition when the case is `under_review`), `POST …/site-visit/decide` (`accept_operator`, `keep_original`, `propose` with a new date), `POST …/site-visit/confirm` (after the deadline), `POST …/site-visit/reschedule`; operator: `POST /applications/{id}/site-visit/accept`, `POST …/site-visit/counter`, `POST …/site-visit/reschedule`; the appointment and its history ride on both views of the application (`site_visit` block: date, slot, state in the reader's words, rounds).

### 4.8 Screens (design pass US-078 fixes the details)

| ID | Screen | Persona | Notes |
|----|--------|---------|-------|
| S-32 | Schedule the site visit (dialog on `OfficerCasePage`) | officer | Propose a date, a slot and a note | UC2-C | FR-043 | Date (DD/MM/YYYY with the calendar glyph), slot as two options with times, note; Propose visit | past date and non-working day refused inline; the sentence "The operator can accept or propose another date; after three working days you can confirm without a reply" | full-screen sheet on tablet | v0.4.0, US-084 |
| S-33 | Appointment card (on the operator's application, S-15) | operator | Accept the proposed visit or propose another date with a reason | UC2-C | FR-043, FR-020 | Accept; Propose another date (date, slot, reason required); Reschedule once confirmed | Waiting for your reply, Waiting for the officer, Confirmed (date and slot), Done; rounds folded below the card | phone first; the card sits under the status line | v0.4.0, US-084 |
| S-34 | Appointment panel (on the officer's case rail) | officer | See the operator's counter-proposal and decide | UC2-C | FR-043 | Accept the operator's date; Keep the original date; Propose another date; Confirm without a reply (disabled with "available from …" until the deadline); Reschedule | the rounds as a small history; "Mark site visit done" disabled with the reason until confirmed | 400 px rail | v0.4.0, US-084 |
| S-30 | Checklist (`ChecklistPage`, `/officer/applications/:id/checklist`) | officer | tablet first: 820 portrait (one-handed) and 1024; item rows grouped by section with the section picker the operator form already uses below 1024; a segmented result control (label plus dot) with the flag toggle stacked under it so no target drops below 44 px; comment field; progress that says counts ("12 of 17 assessed, 3 flagged"); the save indicator with a "Could not save, retrying" tone and an offline banner from `navigator.onLine`; the submit card sticks to the bottom as on Review and submit; one primary action from the server's `actions[]` ("Mark visit done and submit" from `site_visit_scheduled`, "Submit checklist" from `site_visit_done`); read-only after submit; the case page's primary action in both site-visit states is the checklist link, and the "out of scope for this release" paragraph on the case page goes |
| S-31 | Clarification rail (on `OfficerCasePage` in the post-site states) | officer | replaces the feedback rail (locked with a reason); a header line "Round 2, waiting on operator" or "Round 2, your turn" with counts by state; items by round, the current round expanded and earlier rounds folded as `FeedbackNotice` does; each thread rendered with the existing `Timeline` component with the item's own result and comment at the top so the officer never leaves the case to recall it; per-item actions and the transition from `actions[]`; "Not sent yet" on reopened items until the round is requested |
| S-18 | Respond to clarification (`ClarificationRespondPage`, `/app/applications/:id/clarification`) | operator | only flagged items; the officer's comment first on each; response text and a drop zone per item with `capture="environment"` so a phone opens the camera; "2 of 3 files attached" per item; readiness line "Ready to send: 2 of 3 items answered"; a failed send keeps every typed response (the `DocumentSlot` error pattern); confirmation dialog lists the items; after send, a toast and a one-sentence status bar ("The licensing officer is reviewing your responses"); an empty state "Nothing needs your response yet" when the page is reached with nothing open |
| S-19 | Clarification history (on `HistoryPage`) | operator | rounds and the operator's own responses, read-only after sending; earlier visits listed |
| S-40 | Admin overview (`/admin/overview`) | admin | `StatStrip` for the headline numbers, a status table with a bar per row (no KPI grid), the idle list, check health as a definition list, today's runs against the platform quota as metadata text, never a coloured badge (badges are for workflow state) |
| S-42 | Admin activity (`/admin/activity`) | admin | the `AuditTrail` component with its family filters; user-management rows render without a case link; "Show older activity" as a ghost button |
| S-41 | Admin users (`/admin/users`) | admin | `Table` and `SearchBox`; role filter; Change role and Deactivate dialogs; the caller's own row and protected rows show disabled controls with the reason in `title`, before any round trip |
| S-43 | Admin read-only case (`/admin/applications/:id`) | admin | `OfficerCasePage` with `readOnly`: no composer, no rail actions, no item-level clarification controls, no Re-run, no preview link, "Back to the overview" instead of the queue; an `Alert` banner "Read-only: administrators cannot act on a case" |

Every screen verified at 390, 1024 and 1280, the checklist also at 820; the bottom tab bar and the collapsible rail apply to the admin persona too. `DEFINITION_OF_DONE.md` is brought in line with these widths in the plan commit. The artboards (prototype v0.4.0, `docs/04-design/README.md`) went through a critique pass on 20 Sep; `UI_DESIGN.md` pass 3 lists what changed (Reject neutral, chips neutral, no fact badges, the case actions under the rail header, one chronology, viewer-aware copy, phone targets).

### 4.9 Components to reuse (named in the US-078 brief so the new screens do not drift)

`ReviewRail`'s single-primary, disabled-with-reason pattern for every action list; `SaveIndicator` (with the new retrying tone); `Stepper` and the section picker; `DropZone` and `DocumentSlot` for attachments; `FeedbackNotice` for the operator's clarification notice; `Timeline` for threads; `Dialog` with the full-screen sheet on tablet for any dialog that lists items; `StatStrip`, `AuditTrail`, `Table`, `SearchBox`, `Alert` for the admin screens; `StatusBadge` only for workflow status.

### 4.10 Copy for the new dialogs and notifications

Dialogs follow the existing pattern (a question as the title, one or two plain consequence sentences, Cancel plus one primary action, danger style only when the action cannot be corrected inside the product).

| Dialog | Title | Body | Primary |
|--------|-------|------|---------|
| Submit checklist | Submit this checklist? | The findings become final and cannot be edited afterwards. The 3 items you flagged (Coved edges, Chiller temperature, Pest control contract) are sent to the operator with your comments, and the case moves to Awaiting Post-Site Clarification. | Submit checklist |
| Mark visit done and submit | Mark the site visit done and submit this checklist? | The visit is recorded as done, the findings become final, and the 3 flagged items are sent to the operator with your comments. | Mark done and submit |
| Mark site visit done (case page) | Mark the site visit as done? | The application moves to the post-visit stage. Nothing is sent to the operator until you submit the checklist. | Mark done |
| Send responses (operator) | Send your responses? | Your answers and attachments for all 3 items go to the licensing officer. You cannot change them once sent. | Send responses |
| Still needs clarification | Ask again on this item? | The operator's response did not settle it. Write what still needs fixing; the operator sees it when you request another round. (required field: Message for the operator) | Still needs clarification |
| Mark clarified | Mark this item clarified? | This closes the item's clarification. It will not be included in the next round. | Mark clarified |
| Request another round | Send these 2 items back to the operator? | The operator sees only these items with your new comments, and the case moves to Awaiting Post-Site Resubmission until they respond. | Request another round |
| Change role (admin) | Change Lim Jun Hao's role to Licensing officer? (a radio group "New role" above the sentence: Operator, Licensing officer, Administrator) | They get licensing officer permissions on their next request. This does not sign them out. | Change role |
| Deactivate user (admin, danger) | Deactivate Lim Jun Hao? | They cannot sign in until you reactivate the account, and any request they make from now on is refused. Cases stay in the queue for other officers. | Deactivate |

Notifications, in the existing "reference plus one line" style: to the operator at checklist submit, "PF-2026-000231: The licensing officer completed the site visit and needs more information on 3 items"; to the operator on another round, "PF-2026-000231: The licensing officer needs more information on 2 items"; to officers on send, "PF-2026-000231: The operator answered the clarification request"; to the operator on route to approval, the existing status line.

## 5. Admin epic: design decisions (the content of ADR-014)

- **Read model, not a second UI framework.** Read endpoints under `/admin` computed by SQL in `repositories/`: counts by status (drafts as one aggregate row), idle cases from the latest audit row per application, today's submissions and resubmissions from `revision.submitted` events, check health from `verification_runs` over the last 24 hours, runs today from the quota service's own count. "Today" and "idle" are computed on the Singapore calendar day, not UTC midnight and not a rolling window (the quota service's rolling day is right for a quota and wrong for a human "today"). The overview reuses the status query `services/metrics.py` already runs for Prometheus. The admin overview and Grafana serve different readers: the licensing office wants "what is stuck and is the check working" per case; the platform owner wants rates, latency and cost.
- **Routes** as `ARCHITECTURE.md` already lists them: `GET /admin/overview` (the AI-health block replaces the planned `/admin/ai-health`, which is dropped and said so), `GET /admin/audit-feed?limit=50&before=<created_at,id>` (keyset cursor, never `OFFSET`; user-management rows carry `application_id = null`), `GET /admin/users`, `PATCH /admin/users/{id}`, `GET /admin/applications/{id}`.
- **Read-only on applications by construction, at six sites.** Officer GET routes for the queue, the case, the audit trail and the checklist take a new `OfficerOrAdmin` dependency; `feedback-templates` and `licence/preview` stay officer-only (a negative test says so); the three shared operator-or-officer routes in `applications.py` (compare, licence download, document download) gain the admin; the two service-level role checks (`services/licence.py` download, `services/verification.py` re-run) are opened for the download and kept closed for the re-run; `OfficerViewService.build()` computes `actions[]` for the viewer's actor (empty for an admin); every officer mutation keeps `OfficerUser`. The frontend renders the admin's case on `/admin/applications/:id` with `readOnly`, which removes the composer, the rail actions, the item-level clarification controls, Re-run and the preview link, and is an accessibility-gate state of its own.
- **User management as the only admin write.** `PATCH /admin/users/{id}` with `{ "role"?, "is_active"? }`; the service locks the admin rows `SELECT … FOR UPDATE WHERE role = 'admin' ORDER BY id` (a deterministic order so two admins demoting each other serialise instead of deadlocking; a deadlock error, if it ever occurs, is translated to 409 `try_again`), refuses a change that would leave no active admin (409 `last_admin`), refuses a change to the caller's own row (409 `self_change`, which wins when both conditions hold), refuses a protected account (409 `protected_account`), and writes `user.role_changed` (from, to), `user.deactivated`, `user.reactivated` with `application_id = null` and the actor. `AuthService.current_user` already loads the row on every request and `require_role` never trusts the JWT's claim, so a role change or a deactivation takes effect on the very next request; ADR-014 states this as a guarantee and a regression test locks it. `active_officer_ids()` already excludes deactivated officers from notifications; a test covers the new officer notification.
- **Protected accounts.** `users.is_protected` (a new nullable-defaulted column) set by the seed for the operator, officer and admin demonstration accounts. Without it, anyone holding the published password could deactivate the two accounts every reviewer uses. The seed also adds an unprotected spare officer, `officer2@permitflow.example.sg` ("Lim Jun Hao"), for the Playwright admin scenario (which restores it at the end) and for UAT U18.
- **No in-app account creation.** Accounts come from `scripts/seed.py` (which gains `admin@permitflow.example.sg`, "Priya Nair", the shared demonstration password) and a new `scripts/create_user.py`. FR-030 is amended to say so; `SCOPE.md` S7 records it.
- **No "last active".** No column exists and a write on every request for a directory column is not worth it; the directory shows the created date and the role.
- **Threat model.** T19 moves from "planned" to "built as designed" with the protected accounts named; the gap line (MFA for admins, a second admin's approval for a promotion to admin, per-view audit of admin reads) stays as the production requirement.

## 6. Stories to write (in `USER_STORIES.md` and Notion, one to one)

Existing stories get full acceptance criteria in the format of the others; US-071 is marked absorbed by US-070 and closes with it. New stories:

| Story | As a … I want … so that … | Sprint |
|-------|---------------------------|--------|
| US-078 | As the team, I want a design pass for the v0.4.0 screens (checklist, clarification, admin) with their states matrix and the components each reuses, so that the sprints build from agreed artboards and no new screen drifts into its own visual language. | 4 |
| US-079 | As the system, I want the state machine and the workflow service to carry the clarification guards, drop the checklist bypass, allow rejection from the post-site states and take the actor and the notification policy from the caller, so that a site-visited case can neither skip its inspection record nor get stuck, and no one is told the same thing three times. | 4 |
| US-082 | As the owner, I want the per-client limiter to key on the real caller behind the Railway edge, so that one tablet's autosave cannot refuse every other visitor (readiness row 25). | 4 |
| US-080 | As the owner, I want v0.4.0 accepted on the development environment (UAT U13 to U18) and every document brought in line with what exists, so that the release describes itself truthfully. | 8 |
| US-081 | As the owner, I want v0.4.0 released to production by the same ritual as v0.3.0, only when I say so, so that the submitted version stays untouched until then. | on the owner's go |
| US-083 | As an officer, I want the case response to carry `phase`, `outcome` and `can_resolve`, so that the screens stop recomputing server rules (readiness row 22). | 8, SHOULD |
| US-084 | As an officer, I want to propose a site visit date and slot that the operator can accept or counter, so that the visit is arranged inside the case with every round on record. | 5 |

Acceptance criteria for the UC3 stories, to be written verbatim into `USER_STORIES.md`:

- **US-060** `GET /checklist-schema` serves version 1 with seventeen items in five sections; `POST …/checklist` in `site_visit_scheduled` or `site_visit_done` creates the current visit's draft with every item `not_assessed` (201) or returns the existing draft (200), under the application row lock, audited `checklist.created`; any other state answers 409 with the reason; a case scheduled for a second visit gets `visit_no = 2` and the first checklist stays readable; the page renders sections, items, result control, comment and flag at 820 and 1024 without horizontal scroll, and at 390 and 1280; the case page's primary action in both site-visit states is the checklist; operators receive 403 on every checklist route; admins can read, never create or write.
- **US-061** `PUT` with the full item list, `version` and a client `save_id` saves the draft and returns the new version; a replayed `save_id` returns 200 with the current state; a stale `version` returns 409 `version_conflict` with the current content and the page merges the officer's unsaved input over it instead of reloading (another tab's save never silently discards local typing); the client autosaves 1.5 s after the last change and on blur, shows "Saved hh:mm" or "Could not save, retrying", and shows an offline banner while `navigator.onLine` is false; a save after submit answers 409 `checklist_submitted`; no audit row per save.
- **US-062** The flag needs a comment (422 with the item key otherwise); the page shows the count of flagged items and lists them before submit; the confirmation dialog names them; the flag toggle sits under the result control and every touch target is at least 44 px.
- **US-063** Submit requires every item assessed and every flagged or unsatisfactory item commented (422 listing keys); from `site_visit_scheduled` the officer hop to `site_visit_done` is recorded first in the same transaction; on success the findings are frozen, round-1 requests exist and are released for the flagged items, status is `awaiting_post_site_clarification`, the audit trail has `checklist.submitted` and `status.changed` in that order, the operator receives one notification with the count; a second submit answers 409; the case page shows "Checklist submitted on …" with a link to the read-only checklist; the direct route from `site_visit_done` to `pending_approval` no longer exists, and the journey, `04-two-rounds`, `test_licence.py` and `uat_edges.py` submit an all-satisfactory checklist instead.
- **US-064** `GET /applications/{id}/clarifications` returns only items with a released request, each with title, guidance, requests, own responses and an operator-worded status; results and unflagged items are absent from the schema; the operator view carries `clarification: { can_respond, open_count, round }`; the dashboard and list show the case under Needs your response in both operator-turn states with the brief's operator labels, and "Waiting" when nothing is open; the application page shows the clarification notice on top and "Respond to clarification (3 items)" as the primary action; the form and documents are locked with the reason; reached with nothing open, the page says "Nothing needs your response yet".
- **US-065** One response per released open request (409 on a second); text required (≤ 2000); up to 3 attachments per response with the document rules (the fourth is 422 `attachment_cap`; the same bad files are refused as on document upload); an identical file on the same response is "no change"; attachments removable until sent (409 after); the file input offers the camera on phones; `POST /clarifications/send` requires every open item answered (422 listing the unanswered keys), excludes items withdrawn before the send, and moves the case to `post_site_clarification_resubmitted`; officers are notified (deactivated officers are not); audit rows per item and the transition; the confirmation dialog lists the items being sent; a failed send keeps every typed response.
- **US-066** In `post_site_clarification_resubmitted` the officer marks an answered item clarified or asks again with a new message (round N+1 request, unreleased, item open again, shown as "Not sent yet"), or withdraws an open item; "Request another round" is enabled only with ≥ 1 open item, "Route to approval" only with none open or answered, each with the server's reason; the item thread shows every request, response and attachment with author role and timestamp, and the audit trail shows the matching events; a five-round integration test proves nothing is lost; rounds are counted per item; the operator history page shows the rounds and earlier visits; Reject with a note works from all three post-site states, Withdraw keeps working, and an unsent response is shown as "Draft, never sent" after either.

## 7. Tests

| Layer | Additions |
|-------|-----------|
| Unit (pytest) | checklist schema invariants (unique keys, every item in a section, version); completeness rules; the sweep with the regenerated expected table (new edges, removed edges, reject rows, guards); officer next actions; operator labels unchanged; `self_change` wins over `last_admin`; Singapore-day boundary for "today" and "idle" |
| Integration (pytest, PostgreSQL) | the appointment loop (propose, accept, counter, keep, third proposal, reschedule, confirm without a reply after the deadline, done blocked until confirmed, the date rules, every round audited, authorization per endpoint); checklist create (201, 200, two simultaneous first opens), idempotent save replay, conflict merge, submit guards, findings frozen while `clarification_status` still changes, the transition with audit order and a single notification, the system-actor `status.changed` payload identical in shape to an officer one; the second-visit walk (approve path, Return to review, second visit, second checklist); two rounds and a five-round survival test; visibility by construction (exact set, no results, unreleased hidden); attachments (allowlist parity with documents, cap, duplicate, removal before and after send, download by owner, officer and admin, 404 for another operator, 404 for an id from another application); guards on Send responses (an item withdrawn just before send is excluded), Request another round and Route to approval; Reject and Withdraw mid-round with an unsent draft; two officers on one checklist (second save 409); an officer withdraw racing an operator send; admin overview numbers against a seeded fixture including drafts as one row; activity feed keyset order under concurrent inserts and null-application rows; user management (self-change, last-admin, protected account, two admins demoting each other, deactivated user 401, in-flight request completes then 401, role change effective on the next request, deactivated officer not notified, audit rows with null application); admin on officer GETs 200 with `actions: []`, admin 403 on every mutation, on `feedback-templates`, on `licence/preview` and on re-run; authorization matrix for every new route (operator, officer, admin, anonymous, wrong owner) |
| Frontend (vitest) | `ChecklistPage` (autosave timing, merge on conflict, rules, submit reasons, offline banner, retrying tone), the clarification rail (turn line, folded rounds, "Not sent yet"), `ClarificationRespondPage` (only flagged, send disabled with reason, attachment count and errors, input kept on failure, empty state), `HistoryPage` rounds and visits, admin pages (loading, empty, error, dialogs, own row and protected rows disabled, null-application rows), `readOnly` hides item-level controls, router and `RequireRole` for the admin routes, `AppShell` nav per role |
| End to end (Playwright) | `07-site-visit.spec.ts` (schedule → checklist at a 1024 viewport → draft → submit → operator responds with an upload → round 2 → route → approve, audit asserted); `08-admin.spec.ts` (overview, read-only case on a post-site case, role change of the spare officer audited, last-admin and protected-account refusals, spare account restored); `a11y.spec.ts` gains the checklist, respond, history and four admin states; the journey and `04-two-rounds` go through the checklist |
| API edges | `uat_edges.py` gains the visibility, guard and cap checks (about 30) and the officer-only label check goes live for the post-site states |
| Manual UAT | U13 checklist on a tablet in portrait and landscape, U14 submit and automatic move, U15 operator sees only flagged items, U16 respond with attachments and send, U17 two rounds and approval, U18 admin overview, read-only case and a user change on the spare account; recorded in `UAT_PLAN.md` on the development environment |

Coverage thresholds (backend 80, frontend 80) stay in force; frontend coverage sits just above the gate today, so every new page lands with its tests in the same merge; the state-machine doc and the sweep are compared line by line before the Sprint 4 close.

## 8. Documents touched, by hat

| Hat | Files |
|-----|-------|
| Product | `SCOPE.md` (UC3 leaves the Deferred table; new section "v0.4.0"; assumption 6 closed; S7 as built; assumptions 18 to 21: the post-site reading, no revision per clarification round, no check on attachments, the static template), `USER_STORIES.md`, `SPRINTS.md` (Sprints 4 to 8), Notion (Sprint Day options "Sprint 4" to "Sprint 8", UC3 epic name without "(deferred)", stories moved and added) |
| Architect | `REQUIREMENTS.md` (FR-027 amended; FR-030 amended, no in-app creation; FR-036 to FR-042 for UC3; SEC-003 amended; AUD-007), `USE_CASES.md` (UC3-A to UC3-C fully written, UC4-A without create), `STATE_MACHINE.md` (the edge table, the editability row for `pending_post_site_resubmission` reworded to match `editability.py`, side effects), `DOMAIN_MODEL.md`, `ARCHITECTURE.md` (API table: `/admin/ai-health` dropped, the checklist and clarification routes, module list), ADR-013 (checklist and clarification, with the per-state table of section 4.1), ADR-014 (admin read model and user management), ADR README, `DEFINITION_OF_DONE.md` widths |
| Security | `THREAT_MODEL.md` (T19 built; T24 operator reads unflagged content; T25 attachment abuse, the accepted storage gap of T4 now applying twice; T26 findings edited after submit), `SECURITY_REVIEW.md` rows for the new routes |
| Design | `SCREEN_INVENTORY.md`, `UI_STATES.md` (the matrix for the eight screens, before code), `COMPONENT_INVENTORY.md` (the retrying tone, the result control, the clarification thread), `UI_FLOW.md`, `USER_JOURNEY.md`, `UI_REQUIREMENTS_TRACEABILITY.md`, the prototype (new artboards) and the as-built captures |
| DevOps | `OPERATIONS.md` (seed accounts, `scripts/create_user.py`, the release steps and the rollback note), `BRANCHING.md` rule 5 (`v0.<release>.0`), `.env.example` unchanged, `OBSERVABILITY.md` and the dashboard generator if V16 ships |
| Writer | `README.md` (the `dev` notice; scope, demo accounts, tests, what next), `CHANGELOG.md` (Sprints 4 to 8), `RELEASE_NOTES.md` (Unreleased, then v0.4.0), `docs/README.md`, `AI_USAGE.md` (v0.4.0 as an appendix; submitted sections untouched) |
| QA | `TEST_STRATEGY.md`, `UAT_PLAN.md`, `PRODUCTION_READINESS_REVIEW.md` (rows 1, 15 and 25 close; new rows for the admin write path and the attachments), `ASSESSMENT_TRACEABILITY.md` (UC3 section flips from deferred to built), `FINAL_REVIEW.md` addendum |
| Debrief | `notes/DEBRIEF_PREP.md` gains the "why production is frozen" answer and the v0.4.0 status line |

## 9. Release ritual (US-081, only on the owner's go)

1. `dev` green; Sprint 8 close done; `RELEASE_NOTES.md` has the v0.4.0 entry; version set to `0.4.0` in `frontend/package.json` (and its lockfile), `backend/pyproject.toml` (and `uv.lock`) and `backend/app/main.py`, and the `dev` notice removed from `README.md`, in one `chore:` commit on `dev`.
2. Pull request `dev` into `main`; seven checks green; merge (no attribution lines in the body).
3. Tag `v0.4.0` on the merge commit; CI writes the `:v0.4.0` image tags.
4. Stage the production source change to `sha-<merge>` (staged, per environment, never a live connect), review the staged change, accept the deploy.
5. Run the seed in production once (idempotent) to add the admin and the spare officer; verify with a sign-in.
6. Health gates; `/api/v1/metrics` still 401 without the token; Prometheus targets up; PF-2026-001000 compared field for field with the pre-release copy.
7. Rollback: the migrations add tables and one nullable column and reuse the existing notification kinds, so `sha-714a159` can read every row v0.4.0 writes; the previous pin and the same job restore it. The one thing a rollback cannot undo is a case already in a post-site state, which the old code shows with its labels and no checklist screen; `OPERATIONS.md` says so.
8. `OPERATIONS.md` image row, memory and `CHANGELOG.md` updated the same hour.

Timing, fixed by the owner on 20 Sep 2026: `main` is frozen while Xtremax assesses the submission. No pull request, tag or production deploy until the owner lifts the freeze in so many words; a reviewer who asks to see the site visit or the admin panel is pointed at the development environment.

## 10. Risks and how the plan handles them

| Risk | Handling |
|------|----------|
| The reviewers read `dev` | Default branch to `main`, the README notice on `dev`, `AI_USAGE.md` appended not rewritten, working version `0.4.0-dev` |
| The post-site reading | Section 4.1 follows the brief's label grammar and states the alternative; ADR-013 carries the per-state table; the labels themselves are the brief's, verbatim, either way |
| Tablet autosave on a flaky connection | Idempotent saves (a lost response is not a conflict), merge on conflict, the retrying tone and the offline banner; the browser mirror stays parked |
| Sprint size (the Sprint 3 retro) | The design pass has its own half day; the admin epic has its own full sprint with its end-to-end test inside it; V14 and V15 are parked; Sprint 8 is a full day; the cut order starts with the admin epic |
| The officer case page grows past what one file should hold | The checklist is its own route and feature folder (`features/officer/checklist/`); the rail is a sibling of `FeedbackPanel`, not an extension of it |
| The operator respond flow (US-041) assumes the form | The application page branches on the server's `clarification` block; a test covers both phases |
| Frontend coverage just above the gate | Every page lands with its tests in the same merge; the gate is never lowered |
| Migrations and rollback | Additive tables, one nullable column, no new enum values in the 16-character `kind` column; the rollback note in section 9 |
| The interview lands mid-sprint | Every merge into `dev` is a whole story; section 3 says what `dev` shows between sprints; production is untouched by design |
| Beyond-the-brief work grows again | The SHOULD list and the v0.5.0 parking lot are the whole allowance; anything else is a new story on the board for v0.5.0 |

## 11. Decisions the owner is asked to make before Sprint 4 starts

1. The reading of the three post-site statuses: the brief's grammar (section 4.1, recommended; the operator answers right after the checklist is submitted) or the mirror of the pre-site loop (an extra officer release step per round).
2. The checklist bypass `site_visit_done → pending_approval` is removed and the four suites that used it go through an all-satisfactory checklist (recommended), or it is kept behind a guard "no checklist started for this visit".
3. UC3 first, then the admin epic, with the admin epic first in the cut order (recommended), or the admin epic first.
4. Done on 20 Sep 2026 at the owner's request: the GitHub default branch is `main`; `dev` carries the README notice.
5. The three seeded demonstration accounts are protected from the admin write path and a spare unprotected officer is seeded (recommended), or the admin gets a private password instead.
6. Production stays on v0.3.0 until after the Xtremax process (recommended), release only on an explicit go.
7. The seventeen-item checklist grounded in SFA's public requirements (recommended), with the ten-item fallback in the cut order.
8. Clarification attachments without a document check in v0.4.0 (recommended; parked for v0.5.0).
9. In-app account creation stays cut; accounts come from scripts (recommended).
10. Notion: add "Sprint 4" to "Sprint 8" as Sprint Day options and rename the UC3 epic (recommended).

Once these are answered, the first commit of v0.4.0 is `docs: plan v0.4.0` on a `docs/v0-4-0-plan` branch: this file, `SPRINTS.md`, `USER_STORIES.md`, `SCOPE.md`, `DEFINITION_OF_DONE.md`, `BRANCHING.md` rule 5 and the board.

## 12. Review record (20 September 2026, evening)

Three independent reviews of the first draft, each read-only against the brief, the documents and the code. What each changed:

- **Feasibility and consistency review.** Found the default branch (`dev`) exposing the work in progress to the reviewers (section 1); the code encoding both readings of the post-site statuses at once and the brief's grammar favouring the operator-answers-first reading (section 4.1); the untreated `site_visit_done → pending_approval` bypass and the four suites that use it (section 4.1, US-063); the immutable one-per-application checklist blocking a second site visit (section 4.3); the published admin password able to deactivate the demonstration accounts (section 5); Sprint 4 overloaded and the admin epic scheduled before the brief's use case (section 3); `WorkflowService` hardcoding the officer actor and notifying the operator on every hop (section 4.5); the 16-character `notifications.kind` column and the rollback claim (sections 4.5 and 9); autosave auditing flooding the trail and a lost response turning into a false conflict (US-061); the six code sites behind "admin read-only" (section 5); the operator page needing a server fact to branch on (section 4.4); the missing 820 portrait width; the GET-that-creates race (section 4.7); readiness row 25 made worse by autosave (V17); the split of US-066 across sprints; the cut order; the threat numbering (T22 and T23 already exist), FR-030, the planned `/admin/ai-health` route and the editability row; the version rule; Sprint 8's size; the (item, round) uniqueness; the extra 409 between "mark done" and "submit".
- **Product-design review.** Added the offline banner and the retrying tone, the 820 portrait artboard, the single-primary rule through `actions[]`, the sticky submit card, counts in the progress line, the full-screen sheet for list dialogs, the stacked flag toggle, the section picker, the turn line and folded rounds on the rail, the `Timeline` reuse with the item's own result at the top, camera capture and the attachment count on phones, the readiness phrasing, the toast and status bar after send, the empty state before anything is released, input kept on a failed send, disabled controls with reasons on the users page, the component reuse list for the admin screens, facts as metadata rather than badges, the ghost "Show older activity" button, the dialog copy and the notification wording (sections 4.8 to 4.10); parked the photo per item and the reason chips (section 2).
- **QA and security review.** Added the second-visit model, the viewer's actor in `OfficerViewService`, the system-actor transition path and its audit shape, per-item round numbering, the column-level freeze, the row lock for every clarification mutation and the withdraw-versus-send race, the id-ordered admin lock and the deadlock translation, the Singapore-day boundary, the ownership chain on attachment routes, the three shared routes for the admin, no audit row per save, the officer-only label check going live, unsent drafts on a terminal case, two officers on one checklist, the officer-only exceptions to `OfficerOrAdmin`, the keyset cursor and null-application rows, `self_change` precedence, auth freshness as a stated guarantee, "Not sent yet" on reopened items, the cap and post-send error codes, allowlist parity, drafts as one row on the overview, `readOnly` hiding item-level controls, the create race, the dirty-state rule for the checklist autosave and the own-row controls (sections 4.3 to 4.7, 5 and 7).
