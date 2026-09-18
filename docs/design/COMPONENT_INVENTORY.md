# PermitFlow: Component inventory

Components are extracted only where the prototype uses them in two or more places. Names are the intended React component names under `frontend/src/features/shared/` (layout under `frontend/src/app/`).

## Layout

| Component | Variants / props | Used on |
|-----------|------------------|---------|
| `AppShell` | role (operator / officer / admin) → side nav items; top bar with bell count and user chip | every authenticated screen |
| `SideNav` / `BottomNav` | active item, counts; rail column spans the page with the nav stuck to the top and the footer to the bottom; bottom tab bar on phone | all / phone |
| `Breadcrumbs` | items (label, href) | nested screens |
| `PageHeader` | title, subtitle, actions slot | all |
| `Stepper` (locked state) | steps carry `locked` while responding to feedback: lock glyph, not a link (US-040) | S-12 |
| `Field` (trailing) | trailing slot is interactive (password show/hide toggle on sign-in, US-046) | S-00 |
| `Toast` (action) | optional action button (Undo) with a 10 s duration; pressing it closes the toast (US-039) | S-21 |
| `SearchBox` | value, onChange, label (accessible name and placeholder); native clear | My applications, Review queue |
| `StatusBar` | badge (role-aware), explanation, right meta, actions slot; `hasSteps` joins a `Stepper` band | application screens |
| `Stepper` | steps (label, state done / current / attention / todo, href); equal-width grid, connectors fill on completion | S-11, S-12, S-13 |
| `ApplicationHeader` | breadcrumb, reference + licence eyebrow, business name title, status badge + explanation, meta line, actions | S-10 detail, S-11, S-12, S-13 |
| `SectionRail` | sections with completion mark (ok / todo / error / flagged / locked), completion bar, autosave note | S-11, S-15 |
| `Tabs` | items with optional count | S-15, S-16, S-21, S-23, S-25 |
| `StatStrip` | cells: number, uppercase label, context line, optional link, `hot` (primary colour) | S-10, S-20, S-40 |

## Primitives

| Component | Variants | Notes |
|-----------|----------|-------|
| `Button` | primary, secondary, ghost, danger, link; sm; disabled with `title` reason; `asChild` for links | one primary per screen |
| `IconButton` | with badge count | bell |
| `Input`, `Select`, `Textarea`, `Checkbox` | invalid, read-only, focus ring | RHF + Zod |
| `Field` | label (required mark), control, help, error (`role="alert"`) | all forms |
| `FormSection` | title, kicker tag, state (complete / editing / flagged / locked), header actions, footer actions | S-11, S-13, S-15, S-21, S-23 |
| `KeyValueList` | 2-col definition list; muted variant for unchanged | read-only sections |
| `Facts` | horizontal key facts row | S-21 |
| `StatusBadge` | served label + tone; sizes; `live` pulses the dot while something is in progress | everywhere status shows |
| `SaveIndicator` | dirty / saving / saved (relative time, refreshed every 5 s) | section form footer |
| `Toast` (`ToastProvider`, `useToast`) | title, body, tone; bottom-right stack, four max, auto-dismiss 4.5 s (errors stay) | section saved, document uploaded / removed / unchanged |
| `Alert` | tone icon, optional title, optional action slot | inline messages |
| `QueueRow` (in `OfficerQueuePage`) | reference + revision, business + applicant, officer status badge, document-check state (checking / n to check / clear; "to check" counts issues, needs review, unreadable, failed and unavailable, the same set the case card shows as anything but Verified), last activity, next-action chip (ink when it is the officer's turn) | S-20 |
| `CheckResult` | officer-facing verification: outcome, confidence, model, time, issues with code, field and evidence quote, missing information, fixed-vocabulary error reasons | S-21 |
| `ReviewRail` (in `OfficerCasePage`) | server-driven action buttons (primary + secondary, disabled with reason), document-check counts, feedback placeholder | S-21 |
| `FeedbackPanel` | items grouped by round with resolution badge and sent/draft state, anchor link to the target, Withdraw; composer (template select fills target and message, target select, textarea) with per-field 422 errors; locked reason when not under review | S-21 |
| `FeedbackNotice` | operator-facing feedback: open items first with target, resolution (Needs your change / Changed, awaiting review / Resolved), round, message and a link to the target; compact mode folds earlier items | S-15, S-13 |
| `ComparePanel` | revision selectors, change counts, field rows old (struck, red tint) → new (green tint) rendered with the schema's display rules, document add/remove/replace, Show unchanged | S-23 |
| `Reveal` | scroll reveal (IntersectionObserver, once, delay for staggering; reveals immediately without the API) | landing sections |
| `PageSkeleton`, `Skeleton` | shimmer placeholders in the shape of the final layout | every loading state |
| `Badge` | neutral/info/warning/success/error/primary; dot | counts, upload state |
| `Tag` | default, changed, editable, readonly | facts, markers |
| `Alert` | info, warning, error, success, neutral; icon + bold lead | guidance and blocking messages |
| `Toast` | success (dark), with undo/secondary line | after mutations |
| `Dialog` | title as question, body, optional note field, footer (Cancel + primary/danger) | transitions, unsaved changes, remove |
| `Table` | header uppercase, `rowlink` hover, `num` cells nowrap, right-aligned action column; `TableSkeleton`, `TableEmpty` | S-10, S-20, S-25, S-40 |
| `Timeline` | dot kinds (primary/success/warning/info/neutral), title, description, time | S-10, S-14, S-16, S-25, S-40 |
| `EmptyState`, `ErrorState`, `Skeleton` | icon, title, description, action | every data view (UX-002) |

## Domain components

| Component | Responsibility | Used on |
|-----------|----------------|---------|
| `DocumentSlot` | one required document type: empty (drop zone) or `DocumentCard` | S-12, S-15 |
| `DropZone` | idle / dragging / uploading (progress) / error (type, size, duplicate) | S-12, S-15 |
| `DocumentCard` | file name, type, size, uploaded time, upload badge (operator only), `VerificationBlock`, footer actions (download, replace, remove, re-run), "replaces …" line, markers (Changed/Replaced, feedback flag) | S-12, S-13, S-15, S-21, S-23 |
| `VerificationBlock` | 8 states (see DESIGN_SYSTEM), confidence hint, `IssueList` (severity chip, message, evidence), "what to do", officer band (model, latency, advisory) | document cards |
| `FeedbackPanel` / `FeedbackItem` | numbered, target tag, state badge, message, meta, context line; operator variant with "Go to" anchor; officer variant with Edit/Withdraw or Mark resolved/View change; rounds grouped | S-15, S-16, S-21, S-23, phone |
| `InlineFeedbackNote` | officer comment repeated inside the flagged section/document | S-15 |
| `FeedbackComposer` | target select (pre-filled from "Comment on …"), template select + chips, message; disabled with reason outside `under_review` | S-21, S-23 |
| `TransitionActions` | renders every transition allowed for the role from the state machine table; disallowed ones disabled with tooltip; Reject always last, danger | S-21, S-23 |
| `RevisionList` / `RevisionRow` | number, submitted at/by, changed summary, View / Compare | S-16, S-25 |
| `RevisionDiff` | per section: field, old, new; Changed/Added/Replaced marks; unchanged rows recede; hide-unchanged toggle; documents table | S-24 |
| `ChangedFieldValue` | new value highlighted + old value struck through | S-23 |
| `CompletionCard` | percentage bar, sections/documents counts, or "items addressed n of m" | S-11, S-12, S-15 |
| `RequiredDocumentsChecklist` | per-type status line | S-12, S-13 |
| `NotificationsBell` | bell with unread badge; popover with unread tint, title, body, relative time, Mark all as read; Escape and outside click close it; on phones the popover spans the header width below it | S-17 |
| `AuditTrail` | event type (mono), plain summary, actor and role or System, time; family filter with `aria-pressed`; collapsed until opened | S-25, S-40 |
| `PersonaPicker` | prototype/demo only: seeded accounts | S-00 |

## Motion tokens

`--t-fast 150ms` (hover, focus), `--t-base 350ms ease-out` (panel/page fade, dialog), highlight pulse 1.6 s once, indeterminate bar 1.6 s loop, spinner 0.9 s, shimmer 1.4 s. All collapse under `prefers-reduced-motion`.
