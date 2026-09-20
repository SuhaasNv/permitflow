# PermitFlow: UI to requirements traceability

Use cases and requirement IDs from `docs/02-requirements/`. Screens from `SCREEN_INVENTORY.md`.

## Use case → screens

| Use case | Screens |
|----------|---------|
| UC0-A Log in | S-00 Login, S-01 Landing (entry) |
| UC1-A Create and submit | S-10 Dashboard → S-11 Form → S-12 Documents (S-12T tablet) → S-13 Review & submit → S-14 Submitted |
| UC1-B Resubmit with targeted changes | S-17 Notifications → S-15 Application (respond) → S-16 History |
| UC1-C View history and prior feedback | S-16 History, S-24 Compare (read-only) |
| UC2-A Review and request changes | S-20 Queue → S-21 Review workspace → S-22 Request resubmission dialog |
| UC2-B Review a resubmission and compare | S-17 → S-23 Resubmission review → S-24 Compare |
| UC2-C Advance to an outcome | S-21/S-23 header actions + dialogs (site visit, done, route, approve, reject) |
| UC2-D View the audit trail | S-25 History & audit |
| UC3-A Capture the site visit (v0.4.0) | S-21 (Open checklist) → S-30 Checklist (820 and 1024) → submit dialog → S-31 rail |
| UC3-B Answer the flagged items (v0.4.0) | S-17 → S-15 (notice) → S-18 Respond (390 and 1280) → send dialog |
| UC3-C Rounds and the per-item trail (v0.4.0) | S-31 rail (rounds, Not sent yet, Request another round), S-19 History (Site visit tab), S-25 audit trail |
| UC4-A Monitor operations (v0.4.0) | S-40 Admin overview, S-42 Admin activity, S-43 Admin read-only case, S-41 Admin users |

## Requirement → UI element

| Req | Where it is satisfied in the design |
|-----|-------------------------------------|
| FR-001 | S-10 "New application"; S-11 opens as draft |
| FR-002 | S-11 sections from `/form-schema`, typed fields, inline validation |
| FR-003 | S-11 "Draft saved" note, Save and exit, resume from S-10 "Continue" |
| FR-004 | S-12 DropZone per required type, browse fallback, type is the slot |
| FR-005 | S-12/S-15 VerificationBlock with 8 states, polling, no reload |
| FR-006 | S-11/S-12 CompletionCard, S-13 100 % + checklist |
| FR-007 | S-13 Submit (disabled until complete) → S-14 "Submitted" (Revision 1) |
| FR-008, FR-026 | StatusBadge per role; operator screens use operator labels only; S-90 label table |
| FR-009 | S-15 feedback panel above the sections, status bar explanation |
| FR-010 | FeedbackItem target tag (Section / Document type), "Go to" anchor, inline note in target |
| FR-011 | S-15 read-only sections and slots with lock, editable ones with amber "Open for changes" |
| FR-012, FR-013 | S-15 Resubmit → status Pre-Site Resubmitted; S-16 revisions list grows per round |
| FR-014 | S-16 revisions and all released feedback with rounds; S-25 for officers |
| FR-015 | S-20 grouped queue, internal labels, revision + feedback meta, updated, action |
| FR-016 | S-21 sections as KeyValueList, DocumentCards per type with download |
| FR-017 | S-21/S-23 VerificationBlock with confidence, issues, evidence, missing info, re-run |
| FR-018 | S-21 FeedbackComposer (target, template, message), Edit/Withdraw only while Under Review, "not yet released" tag |
| FR-019 | TransitionActions: only allowed targets enabled, Reject always available with note |
| FR-020, FR-021 | S-17 NotificationsPanel kinds submitted / resubmitted / status_changed; bell count |
| FR-022 | S-23 "Changed" / "Replaced" markers, unchanged sections collapsed |
| FR-023 | S-24 RevisionDiff (field-level, document-level), selectors (S4) |
| FR-024 | FeedbackItem states Open → Addressed in Rev N → Resolved; Mark resolved |
| FR-025 | S-25 AuditTable, Status history |
| FR-027 | Header actions and dialogs for site visit, done, route to approval, approve, reject |
| FR-027 (follow-ups) | Approve dialog warning on unresolved check results; Return to review action and dialog (S-21) |
| FR-028 | S-00; role home routing; staff sign-in link |
| FR-031 | S-01 landing page |
| FR-032 | S-11 aside Withdraw application with danger dialog and optional reason; S-11b withdrawn outcome panel; officer S-21 withdrawal notice |
| FR-033 | S-21 Mark resolved only on released items, Undo toasts, Not fixed reopen |
| FR-034 | S-11 Discard draft / Delete draft dialogs |
| FR-035 | S-26 licence preview page; S-21 licence block with download after approval; S-11b Download licence (PDF) in the outcome panel |
| FR-029 | S-40 stat strip, status table with bars, idle list, check health as a definition list, today's counts and the platform quota as metadata (v0.4.0 design) |
| FR-030 | S-41 users table with Change role and Deactivate or Reactivate dialogs (no in-app creation, FR-030 amended), own and protected rows disabled with the reason; S-42 activity feed; S-43 read-only case with the banner |
| FR-036, FR-037 | S-30 checklist opens from S-21 once a visit is scheduled; one checklist per visit; seventeen items in five sections with result, comment and guidance |
| FR-038 | S-30 autosave: Saved hh:mm, retrying, offline banner, merge on conflict (`UI_STATES.md`) |
| FR-039 | S-30 `FlagToggle` with the required comment |
| FR-040 | S-30 submit dialog listing the flagged items; the case moves on its own; S-31 shows the released items as Open |
| FR-041 | S-18 shows only the flagged items with the officer's comment first; response and up to three attachments per item; readiness line; Send responses |
| FR-042, AUD-007 | S-31 threads with rounds, S-19 history per visit, S-25 audit events per item |
| SEC-003 (amended) | S-43: admin reads the officer's case with no control rendered; every mutation 403 on the server |
| NFR-007 | S-40 AI health (latency, outcomes) |
| SEC-001–003 | Route guards + "Not available for your role" panel (S-90); operator views never include internal fields |
| SEC-004 | Disabled transitions with reason; 409 handling |
| SEC-005 | S-12 accepted-files card, client + server validation messages, duplicate (sha256) message |
| SEC-006, SEC-010 | S-00 session note, 429 message |
| SEC-008 | Officer sees `possible_prompt_injection` as a Needs review issue with the flagged phrase |
| AI-002 | VerificationBlock fields map 1:1 to the result schema |
| AI-005 | "Advisory only" band; AI never appears in TransitionActions or feedback state |
| AI-006 | `unavailable` state copy "you can still submit"; S-13 warning, submit enabled |
| AI-009 | Re-run check on terminal states |
| AUD-001–006 | S-25 |
| UX-001 | DESIGN_SYSTEM tokens |
| UX-002 | UI_STATES per screen |
| UX-003 | S-11 error summary + inline errors |
| UX-004 | FeedbackItem "Go to", highlight pulse |
| UX-005 | StatusBadge everywhere status shows |
| UX-006 | S-24 old/new columns with marks |
| UX-007 | MobileDashboard, MobileApplication, TabletDocuments artboards; responsive rules in FRONTEND_ARCHITECTURE |
| UX-008 | focus ring, aria-labels, non-colour status signals (dot/icon + label) |
| REL-001, REL-005 | ErrorState with request id + Retry; mutation errors preserve input |
| REL-007 | 409 reload banner |

## Stories → screens

US-001 S-00 · US-010 S-10/S-11 · US-011 S-11 · US-012 S-12 · US-013 S-12 (VerificationBlock) · US-014 CompletionCard · US-015 S-13/S-14 · US-016/017/018 S-15 · US-019 S-16 · US-020 S-20 · US-021/022/023/024 S-21 · US-025 S-22 + TransitionActions · US-026 S-17 · US-027 S-23/S-24 · US-028 S-23 · US-029 S-25 · US-030/032 StatusBadge · US-031 dialogs · US-070/071/072 S-40 · US-073 S-41 · US-009 (this phase) all.
