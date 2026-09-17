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

Public Sans (Google Fonts) for everything; IBM Plex Mono for references, UENs and audit event types. Scale in `DESIGN_SYSTEM.md`. Body is 15/22: deliberately larger than typical SaaS because forms and officer comments are read carefully. Table headers are 12 px uppercase with letter-spacing; metadata 12 px in text-3. Numerals are tabular everywhere counts and dates appear.

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

Still open from pass 2 (judged acceptable for the MVP, listed for the frontend build): the landing hero could carry more product evidence; the success screen is a conventional centred card; the disabled-button token should be verified against the built component.

## Assumptions made during design

1. Operators see a single "Submitted" badge after submission (the operator label for `application_received`); the confirmation screen also shows the reference and a plain-language "what happens next".
2. The operator dashboard uses a stat strip rather than the C1 summary cards in SCOPE (same information, different form); C1 remains COULD-HAVE.
3. On the operator resubmission screen, sections without feedback are shown read-only and collapsed to key/value, not hidden, so "previous information never appears lost" (FR-011, FR-014).
4. The officer resubmission screen is designed in `under_review` (after "Start review"), because feedback can only be resolved in that state (STATE_MACHINE feedback rules). The queue row's primary action for a `pre_site_resubmitted` case is "Review resubmission", which performs Start review.
5. Confidence is shown to officers only (small bar + number, titled "a hint, not a decision"). Operators never see a confidence number; they see the state, a plain explanation and what to do.
6. "Upload complete" and the verification state are two separate indicators on a document card (upload badge in the header, verification block below), per the brief's requirement that the two lifecycle stages are distinguishable.
7. Notifications are a panel from the bell; no separate notifications page in the MVP (the sidebar item opens the same panel).
8. Admin is a single overview screen (concept only).
