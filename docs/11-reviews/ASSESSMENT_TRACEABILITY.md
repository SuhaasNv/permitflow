# Assessment traceability

Every line of the brief that can be checked, against where it is implemented, where it is tested, and where the evidence lives. Written 19 Sep 2026 against `dev` before the v0.3.0 release. Status: **Met**, **Partly**, **Deferred** (deliberately, in `SCOPE.md`) or **Beyond** (built beyond the brief).

## What the brief asks for (decoded)

The email: a 3-day take-home for a Full Stack Developer role, submitted by replying to the email; selected candidates discuss the assessment and the approach at an on-site interview in Singapore.

The brief, in one paragraph: build a regulatory licensing platform with two roles named in the brief (operator, officer) plus the system as an actor; this build adds an admin role, beyond the brief, pick which of three use cases to build, write `SCOPE.md` before code (what is built, deferred, mocked; assumptions; stack in 3 to 5 sentences), use AI tools but document how in a README section called "AI Usage" (tools and tasks, example prompts, how output was verified, what was discarded), ship a README with setup steps, stack justification and a "What I would do next" section, keep secrets out of the repository, handle errors and validate input on key paths, and follow the status mapping table exactly with different labels per role. Evaluation: scope judgement, production readiness, AI tool usage, code quality, documentation and communication, and an honest debrief.

## Deliverables and submission checklist

| Brief item | Status | Where |
|------------|--------|-------|
| Working codebase that runs with the README steps | Met | `README.md` "Run locally" (Docker, uv, Node 24; about ten minutes); verified from a clean clone at each sprint close |
| `SCOPE.md`: built, deferred, mocked, why; assumptions; stack in 3 to 5 sentences | Met | `SCOPE.md` (MUST/SHOULD/COULD/DEFERRED tables, 17 assumptions, stack paragraph, sprint checks) |
| README "AI Usage" (tools, prompts, verification, discarded output) | Met | `README.md` "AI Usage"; full record `AI_USAGE.md` |
| README "What I would do next" | Met | `README.md`; severity table in `PRODUCTION_READINESS_REVIEW.md` |
| Stack justified in the README | Met | `README.md` stack paragraph; `docs/03-architecture/decisions/ADR-009` |
| Error handling and input validation on key paths | Met | Error envelope `{error: {code, message, details?}}` everywhere (`backend/app/main.py`); Pydantic 422 with per-field details; upload allowlist, size, magic bytes (`domain/uploads.py`); 409 for invalid transitions and version conflicts; frontend inline validation from the server schema (`zodFromSchema`); 429 with `Retry-After` on every route and 409 `draft_limit` (US-058) |
| No secrets committed | Met | gitleaks in CI over full history; `.env` ignored; `.env.example` documents every variable; tokens set as GitHub environment secrets; pip-audit, bandit and npm audit block the build (US-058) |
| Honest account of the work | Met | `AI_USAGE.md` sections 5 and 6 (verification, what was wrong or discarded), `ISSUES_AND_MITIGATIONS.md`, `FINAL_REVIEW.md` |

## Use case 1: operator submission and resubmission

| Acceptance criterion | Status | Implementation | Tests | Evidence |
|----------------------|--------|----------------|-------|----------|
| Complete form data entry | Met | Four sections from a server-defined schema (`domain/form_schema.py`), autosave per section, inline validation (`SectionForm.tsx`) | `test_sections.py`, `SectionForm.test.tsx` | Journey spec step 1 |
| Document uploads with drag-and-drop | Met | `DropZone.tsx`, four typed slots, replace and remove, duplicate detection by sha256 | `test_documents.py`, `test_uploads.py` | Scenario 01 |
| Real-time AI verification status per document | Met | Background run per upload, polling every 2 s while pending, eight states with plain-language copy (`VerificationBlock.tsx`) | `test_verification.py`, `verification_summary` tests | Scenario 01, run-throughs |
| Progress indicator of overall completion | Met | Server-computed completeness (`domain/completeness.py`), `CompletionCard.tsx`, stepper | `CompletionCard.test.tsx` | Journey |
| Status "Pending Pre-Site Resubmission" | Met | Label table `domain/labels.py`, verbatim from the brief | `test_labels.py` | Scenario 03 |
| Officer comments prominently at the top | Met | `FeedbackNotice.tsx` above the application on the operator page | `ApplicationPage.test.tsx` (feedback placement: the notice precedes the sections in DOM order, each item links to its target; added 20 Sep after a review found the row untested) | Scenario 03 |
| Feedback linked to the specific section or document | Met | Every feedback item carries `section_key` or `document_type`; links jump to the target; the target shows the comment inline | `test_feedback.py` | Scenario 03 |
| Operator updates only the flagged sections; no need to re-enter everything | Met, enforced | Editability derived from open released feedback; other sections 403 (`services/applications.py`); respond mode walks flagged targets only (`respond.ts`) | `test_resubmission.py` (403 on unflagged section) | Scenario 04 |
| Multiple rounds supported seamlessly | Met | Unlimited rounds; each round a new immutable revision; Not fixed reopens for the next round | `test_resubmission.py`, `test_feedback_reopen.py` | Scenario 04 (two rounds) |
| Application data never lost between rounds | Met | `ApplicationRevision` snapshots, working copy kept, old documents retained with `is_current=false` | `test_resubmission.py`, `test_compare_and_resolution.py` (revision 1 unchanged) | Scenario 04 compare |
| Revision history and previous comments visible | Met | `HistoryPage.tsx`, compare endpoint | `test_compare_and_resolution.py` | Scenario 04 |

## Use case 2: officer review and feedback

| Acceptance criterion | Status | Implementation | Tests | Evidence |
|----------------------|--------|----------------|-------|----------|
| Full submission, organised | Met | Case page: sections, documents, checks, feedback rail, revision history, audit (`CasePage.tsx`) | `test_officer_case.py`, `CasePage.test.tsx` | Scenario 02 |
| AI results and flagged issues visible | Met | Per-document `CheckResult` with confidence, evidence, model; summary card | `test_verification_summary.py` | Run-through 2 |
| Request more information with contextual comments | Met | Feedback tied to section or document, draft until released | `test_feedback.py` | Scenario 03 |
| Predefined comment templates | Met | Seven templates (`domain/feedback_templates.py`), editable before sending | `test_feedback.py` (templates) | Scenario 03 |
| Status change triggers operator notification | Met | Notification row in the same transaction as the transition; bell with unread count | `test_notifications.py` | Scenario 02 |
| Officer notified on "Pre-Site Resubmitted" | Met | `resubmitted` notification to every active officer | `test_notifications.py` | Scenario 02 |
| Updated sections highlighted; only changes surfaced | Met | Changed and Replaced markers, unchanged sections collapsed, "Addressed in Revision N" | `test_compare_and_resolution.py` | Scenario 04 |
| Compare against previous versions | Met | Any two revisions, field-level and document-level diff (`domain/diff.py`) | `test_diff.py`, `test_compare_and_resolution.py` | Scenario 04 |
| Resolution of flagged issues tracked | Met | open → addressed (automatic) → resolved (officer), withdrawn, reopen; undo | `test_feedback.py`, `test_feedback_undo.py` | Scenario 04 |
| No applications lost to transitions or filtering | Met | State machine as data with exhaustive tests; row lock and version check; reject and withdraw from every non-terminal state; queue lists every non-draft application | `test_workflow.py` (588 combinations), `test_outcome.py`, `test_edge_cases.py`, `test_officer_queue.py` | |
| Complete audit trail of feedback and rounds | Met | Append-only `audit_events` in the same transaction, officer audit page with plain-language summaries | `test_audit_trail.py` | Every scenario ends on the audit trail |
| Unlimited resubmission cycles | Met | No round limit anywhere | Scenario 04 (two rounds), `test_resubmission.py` | |
| Status mapping followed; different labels per role | Met verbatim | `domain/labels.py` | `test_labels.py` asserts the table for both roles | |
| Operators cannot see the internal approval stage | Met (see SCOPE assumption 17) | Operator response models carry labels only; "Pending Approval" is the brief's own operator label; decision note only with the outcome | `test_officer_case.py`, `test_notifications.py` | |
| Operators see only the final outcome | Met | Approved or Rejected panel with the note | `ApplicationPage.test.tsx` | Scenario 06 |

## Use case 3: site-visit checklist

| Acceptance criterion | Status | Note |
|----------------------|--------|------|
| Checklist capture, draft save, per-item "Need Further Clarification", automatic move to Awaiting Post-Site Clarification, operator sees only flagged items, per-item response with uploads, multiple rounds with audit | Deferred | `SCOPE.md`; the three post-site statuses, their transitions and labels exist and are unit-tested (`test_workflow.py`); stories US-060 to US-066 recorded Not started on the board |

## Beyond the brief (product decisions, all marked in SCOPE.md)

Product: withdraw with reason (US-038), delete draft (US-045), feedback undo (US-039) and reopen (US-049), respond-mode walk (US-041), search (US-036), landing page (FR-031), licence certificate with preview and download (US-051), the owner's domain (US-052).

Engineering and assurance, all on the last day: coverage thresholds in CI (US-053), a live AI evaluation workflow (US-054), LangSmith tracing (US-055), the six-stage AI gate with a fairness check (US-056), the legal, privacy and accessibility review with policy pages and an axe gate (US-057), abuse resistance with rate limits, quotas, CSP and blocking audits (US-058); Return to review (US-031 follow-up), custom domain (US-052), admin role reserved (US-070 to US-073 not built).

## Evaluation areas

| Area | Where to look |
|------|---------------|
| Scope judgement | `SCOPE.md`, `docs/05-planning/SPRINTS.md` (cut order), `FINAL_REVIEW.md` |
| Production readiness | `PRODUCTION_READINESS_REVIEW.md`, `docs/06-security/THREAT_MODEL.md`, `docs/06-security/SECURITY_REVIEW.md`, `docs/11-reviews/LEGAL_AND_ACCESSIBILITY_REVIEW.md`, `docs/09-operations/OPERATIONS.md`, `.github/workflows` |
| AI tool usage | `README.md` "AI Usage", `AI_USAGE.md` |
| AI assurance | `docs/07-ai/AI_ASSURANCE.md`, `docs/07-ai/AI_EVALUATION.md`, `.github/workflows/ai-gate.yml`, `ai-eval.yml` |
| Code quality | `docs/03-architecture/ARCHITECTURE.md`, `tests/unit/test_layering.py`, mypy strict and TypeScript strict in CI |
| Documentation and communication | `docs/README.md` index, `CHANGELOG.md`, this file |
