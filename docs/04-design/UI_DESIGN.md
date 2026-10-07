# PermitFlow: UI design direction

## One line

A Singapore government licensing service that feels like a well-made enterprise product: calm, precise, trustworthy, with colour reserved for meaning and typography carrying the hierarchy.

## Inspiration and boundaries

Inspiration is the design philosophy behind Singapore's digital government services (clarity, accessibility, predictable interactions, strong information hierarchy, restrained visual language). No Singpass branding, screens, logos or distinctive layouts are reproduced. PermitFlow has its own identity: the "PF" mark, Public Sans, a deep red primary used sparingly (REQ UX-001: deep red accent, charcoal text, light canvas).

## Personality

Premium · clean · calm · trustworthy · modern · functional · precise · human.

The UI earns its quality through precision (alignment, spacing, type scale, tabular numerals) rather than decoration.

## What we deliberately avoid

| Avoided | Why | What we do instead |
|---------|-----|--------------------|
| KPI card grids ("4 identical tiles") | reads as generic admin template | one stat strip with number + uppercase label + one-line context, cells are links |
| Gradients, glassmorphism, big shadows | AI-template look, hurts readability | 1 px borders, 1–2 px shadows, flat surfaces |
| Everything rounded | softens a serious service | 6 px controls, 10 px containers, 12 px pills only for badges |
| Emoji, decorative illustrations, hero sections | noise | inline stroke icons only where they carry meaning (status, action) |
| Over-badging | badge fatigue makes real status invisible | one status badge per row/header; tags (grey) for facts; badges only for state |
| Developer-style diffs | not a business audience | field-by-field old/new table with plain "Changed / Replaced" marks; unchanged rows recede |
| Dark-mode developer aesthetic | not the audience | light canvas, dark toast only |
| Lorem ipsum, John Doe | credibility | fictional Singapore data: businesses, UENs, addresses, document filenames, officer comments |

## Colour

- **Primary red `#A8192A`**: brand mark, one primary action per screen, "needs you" signal in the stat strip. Never used for decoration, headers or large surfaces.
- **Canvas `#F3F4F6` / surface `#FFFFFF`**: content lives on white surfaces over a cool light canvas.
- **Text `#1B2430` / `#465060` / `#66717F`**: three tiers; all ≥ 4.5:1 on white.
- **Semantic**: success green (verified, resolved, approved), warning amber (needs the operator, needs review, open feedback), error red (validation, issues found, failed, rejected, blocked), info blue (in progress with the office, changed, addressed), neutral grey (draft, unchanged, unreadable/unavailable, historical).
- Colour is never the only signal: every badge has a dot or icon and a label; verification states have distinct icons; diff rows have text marks.

Status badge colour groups follow the state machine: neutral = draft; info = states where the office is acting (Submitted/Application Received, Under Review, Resubmitted, Site Visit…, Pending Approval); warning = states where the operator must act (Pending Pre-Site Resubmission, Pending Post-Site Resubmission); success/error = terminal.

## Typography

Public Sans (self-hosted since US-057, OFL) for everything; IBM Plex Mono for references, UENs and audit event types. Scale in `DESIGN_SYSTEM.md`. Body is 15/22: deliberately larger than typical SaaS because forms and officer comments are read carefully. Table headers are 12 px uppercase with letter-spacing; metadata 12 px in text-3. Numerals are tabular everywhere counts and dates appear.

## Composition rules

- One page title per screen, left; primary action top-right; breadcrumbs above the title when the screen is nested.
- A **status bar** directly under the page header on every application screen: badge, one-sentence explanation in plain language, revision/date on the right, actions right-aligned for officers. The user always knows *where they are, what state it is in, what to do next* (core UX principle).
- Operator form screens use a **240 px section rail** left (section list with completion marks, completion bar, autosave note) and content right. Officer screens use a **400 px feedback rail** right (feedback list, composer, allowed next steps) because feedback is the officer's output.
- Officer screens are denser (13–14 px in tables) but keep the same components.
- Unchanged content recedes (grey text, collapsed sections) so change is what the eye lands on.

## Motion

Short, purposeful, reduced-motion aware (`prefers-reduced-motion` collapses all animation to ~0). Used for: page/panel fade-in (350 ms), hover/focus transitions (150 ms), verification progress bar and spinner while a check runs, one-time highlight pulse when a feedback anchor scrolls to its target, skeleton shimmer, toast entry. Not used for: decorative reveals, parallax, bouncing.

## Accessibility (design-time commitments)

Real `<button>`/`<a>`/`<input>`+`<label>` in the prototype; visible 2 px focus ring; all semantic colours ≥ 4.5:1; status never colour-only; touch targets ≥ 40 px (44 px primary on phone); error summaries at the top of a form plus inline errors with `role="alert"`; dialogs are `role="dialog" aria-modal`; icon-only buttons carry `aria-label`.

## Critique passes (independent design-review agent)

| Pass | Score | Main findings | Applied |
|------|-------|---------------|---------|
| 1 (17 Sep) | 6.6 / 10 | KPI tile grids read as template; red doing five jobs; 11 layout bugs (clipped audit table, wrapped steppers, squeezed status bars); login marketing pane; model name and latency exposed to officers | KPI tiles replaced by an action card, grouped queue and prose stats; references mono charcoal; timeline dots info; Reject neutral; composer stacked; model and latency removed from officer view; all layout bugs fixed |
| 2 (18 Sep) | 6.9 / 10 | Tablet artboard was a desktop clone (build bug); officer titles wrapped under four actions; one seed dataset leaked across applications; primary-soft used for selected, active and error states; admin overview still a KPI row; confidence meters shown to operators | Tablet build fixed; officer header reduced to two actions plus overflow, Compare moved into the status bar; PF-2026-000231 given its own Clementi data; active nav and radio states neutral with a 3 px rule; admin numbers folded into a sentence; confidence hidden from operators; date fields as text with calendar icon; login given the "before you start" list |

| 3 (20 Sep, v0.4.0 artboards) | 5.5 to 7 per artboard | Reject drawn in danger style; selected chips and the section picker in primary-soft (a pass-2 regression); a "Healthy" badge for a fact; the active phone tab in red; the case actions at the foot of a 2,500 px rail; four-column number grids on the admin overview (KPI tiles by another name); a five-number checklist card; the demo chronology impossible under the state machine; the send dialog open on a disabled Send; officer-voiced copy on the admin's read-only case; 36 px attach targets and a send card behind the tab bar on the phone; "Save and leave" beside "it saves as you go"; an offline promise the design does not keep; jargon (p95, LangSmith, command line) on the admin screens; shell drift from the shipped `AppShell` | Reject secondary; chips and picker neutral-soft with charcoal text; the checks panel header says "1 of 38 checks failed"; phone tab charcoal with the neutral pill; Next step block under the rail header with counts as one text line; definition lists (label left, number right) and a one-sentence checklist card; one chronology across the three operator boards and the rail; the dialog board fully answered; viewer-aware copy; 44 px targets and the send card above the tab bar; "Next unassessed" and "Retry save" in place of "Save and leave"; the offline banner says "keep this page open"; "Slowest 5 % of checks", "set up by the service team"; masthead, avatar, Sign out, nav kicker, footer and the document mark mirrored from `AppShell.tsx`; a phone board with the send dialog as a sheet and one drawn focus ring; the role radio group in the Change role dialog; references in charcoal mono; numeric table headers right-aligned |

Still open from pass 2 (judged acceptable for the MVP, listed for the frontend build): the landing hero could carry more product evidence; the success screen is a conventional centred card; the disabled-button token should be verified against the built component.

## Assumptions made during design

1. Operators see a single "Submitted" badge after submission (the operator label for `application_received`); the confirmation screen also shows the reference and a plain-language "what happens next".
2. The operator dashboard uses a stat strip rather than the C1 summary cards in SCOPE (same information, different form); C1 remains COULD-HAVE.
3. On the operator resubmission screen, sections without feedback are shown read-only and collapsed to key/value, not hidden, so "previous information never appears lost" (FR-011, FR-014).
4. The officer resubmission screen is designed in `under_review` (after "Start review"), because feedback can only be resolved in that state (STATE_MACHINE feedback rules). The queue row's primary action for a `pre_site_resubmitted` case is "Review resubmission", which performs Start review.
5. Confidence is shown to officers only (small bar + number, titled "a hint, not a decision"). Operators never see a confidence number; they see the state, a plain explanation and what to do.
6. "Upload complete" and the verification state are two separate indicators on a document card (upload badge in the header, verification block below), per the brief's requirement that the two lifecycle stages are distinguishable.
7. Notifications are a panel from the bell; no separate notifications page in the MVP (the sidebar item opens the same panel).
8. Admin was a single overview screen (concept only) in v0.3.0; the v0.4.0 design (20 Sep 2026) makes it four screens: overview, activity, users and the officer's case page read-only, all assembled from the shipped components (`COMPONENT_INVENTORY.md`, v0.4.0 section).
9. The officer's checklist is designed portrait first (820, one hand on an iPad) and then at 1024; result and flag controls are 44 px; the page never has more than one primary action, taken from the server's `actions[]`.
10. Clarification threads show the officer's finding once, at the top of each thread, and the requests carry only what was added; earlier rounds fold; the case-level decision sits under the rail header, per-item decisions sit under each thread.
11. Facts (a result, a count, a health figure) are tags or plain text, never badges; badges remain for workflow state only, so the admin overview carries no coloured "Healthy" badge and no KPI grid.
