# PermitFlow: Design system (v0.1)

Rendered on the "Design system" artboard of the prototype. Values become Tailwind theme tokens (`tailwind.config.ts`) and CSS variables in `frontend/src/styles/`.

## Colour tokens

| Token | Value | Use |
|-------|-------|-----|
| `bg` | `#F3F4F6` | page canvas |
| `surface` | `#FFFFFF` | cards, tables, forms |
| `surface-2` | `#F9FAFB` | table header, card footer, read-only fields |
| `line` / `line-strong` | `#D9DEE5` / `#AEB6C2` | borders / input borders |
| `text` / `text-2` / `text-3` | `#1B2430` / `#465060` / `#66717F` | primary / secondary / metadata |
| `primary` / `primary-hover` | `#A8192A` / `#8A1422` | brand, primary action, attention |
| `primary-soft` / `primary-line` | `#FBEDEE` / `#EFB8BE` | active nav, primary badge |
| `success` / soft / line | `#067647` / `#ECFDF3` / `#A6E9C4` | verified, resolved, approved, complete |
| `warning` / soft / line | `#9A4A00` / `#FFF6E5` / `#F5CF86` | needs operator, needs review, open feedback |
| `error` / soft / line | `#B42318` / `#FEF3F2` / `#F4B7B1` | validation, issues found, failed, rejected |
| `info` / soft / line | `#175CD3` / `#EEF4FF` / `#B2CCFA` | in progress, changed, addressed |
| `neutral` / soft / line | `#475467` / `#F2F4F7` / `#D0D5DD` | draft, unchanged, unavailable |
| `focus` | `#175CD3` | 2 px focus ring, 2 px offset |

Contrast: all `text*`, `success`, `warning`, `error`, `info`, `primary` ≥ 4.5:1 on white and on their soft backgrounds.

## Type scale (Public Sans for UI; Instrument Serif for display; IBM Plex Mono for identifiers)

Three families, each with one job: Public Sans carries every control, label and body line; Instrument Serif (regular only, tight leading) is reserved for display moments that address the person rather than the task (landing hero, sign-in, dashboard greeting, "Application submitted"); IBM Plex Mono marks identifiers and ordinal numbers (`01`, references, counts).

| Style | Size / line | Weight | Use |
|-------|-------------|--------|-----|
| Display serif | 44 to 72 / 1.02 | 400, Instrument Serif | landing hero; 34 to 40 for landing section titles |
| Greeting serif | 36 to 42 / 1.05 | 400, Instrument Serif | dashboard greeting, sign-in title, submitted title |
| Page title | 28 / 36, tracking -0.015em | 600 | one per screen |
| Form section title | 22 / 28 | 600 | section form header |
| Section heading | 17 / 24 | 600 | review summaries, side panels |
| Section title | 20 / 28 | 600 | dialogs, design-system sections |
| Subsection | 16 / 24 | 600 | card headers, form sections |
| Body | 15 / 22 | 400 | default |
| Supporting | 13 / 20 | 400 | help text, table cells, metadata lines |
| Label | 13 / 18 | 600 | form labels; table headers 12 uppercase +0.04em |
| Metadata | 12 / 16 | 400, text-3 | timestamps, counters |
| Eyebrow | 12 / 16 | 600 uppercase +0.08em | section kickers |
| Mono | 13 | 400 | references, UEN, sha256 prefix, audit event type |

## Spacing, radius, elevation

- Spacing scale: 4, 8, 12, 16, 20, 24, 32, 40. Page padding 24×32; card padding 20; card header 14×20; table cell 14×16.
- Radius: 4 (tags), 6 (controls, small cards), 10 (containers), 12 (badges pill).
- Elevation: `shadow-1` (1 px hairline) only on secondary buttons; panels are one bordered white surface (`.pf-surface`) with no shadow; `shadow-2` for toasts; `shadow-3` for dialogs. Never a card inside a card: hierarchy comes from rules (`divide-y`), whitespace and type.
- Layout: masthead 28; top bar 56 (sticky, blurred); side nav 232, collapsed 64 (width animates 220 ms); bottom tab bar 64 on phones; content column max 1360 with 16 / 32 / 40 px gutters; officer feedback rail 400.

## Motion

Tokens in `frontend/src/styles/index.css`: `--ease-out` cubic-bezier(0.2, 0, 0, 1), `--dur-fast` 150 ms (hover, focus, press), `--dur-base` 220 ms (dialogs, rail collapse, badge tone change), `--dur-slow` 320 ms (page and panel entrance). Utilities: `.pf-enter` (6 px rise + fade, keyed on the route in `AppShell`), `.pf-stagger` (children enter 40 ms apart), `.pf-check` (check mark draws itself), skeleton shimmer 1.4 s, toast in 320 / out 220 ms, verification progress steps advance every 700 ms while the server run is pending. Buttons settle 1 px on press. `prefers-reduced-motion` collapses every animation and transition to 1 ms.

## Status badge vocabulary (as rendered)

Badge = dot + label, 24 px (28 px "lg" in status bars). Labels are the role-specific labels from `STATE_MACHINE.md`; the operator client never receives the internal code.

| Internal | Officer badge | Operator badge | Colour |
|----------|---------------|----------------|--------|
| draft |: | Draft | neutral |
| application_received | Application Received | Submitted | info |
| under_review | Under Review | Under Review | info |
| pending_pre_site_resubmission | Pending Pre-Site Resubmission | Pending Pre-Site Resubmission | warning |
| pre_site_resubmitted | Pre-Site Resubmitted | Pre-Site Resubmitted | info |
| site_visit_scheduled | Site Visit Scheduled | Pending Site Visit | info |
| site_visit_done | Site Visit Done | Pending Post-Site Clarification | info |
| awaiting_post_site_clarification | Awaiting Post-Site Clarification | Pending Post-Site Clarification | info |
| pending_post_site_resubmission | Awaiting Post-Site Resubmission | Pending Post-Site Resubmission | warning |
| post_site_clarification_resubmitted | Post-Site Clarification Resubmitted | Post-Site Resubmitted | info |
| pending_approval | Route to Approval | Pending Approval | info |
| approved | Approved | Approved | success |
| rejected | Rejected | Rejected | error |

## Tags (facts and markers) vs badges (state)

Tags are 22 px, 4 px radius: neutral (facts such as "Section: Premises"), `changed` (info: Changed, Replaced), `editable` (warning: Open for changes, n feedback items), `readonly` (neutral with lock). Badges are pills reserved for state (application status, upload state, feedback state, verification outcome). Disabled buttons use the neutral-soft fill and text-3, never a tinted primary. Active navigation uses neutral-soft with a 3 px primary rule, not primary-soft. Date fields are text inputs (DD/MM/YYYY) with a calendar icon, not native date pickers.

## Verification state vocabulary (as rendered)

Icon in a 28 px tinted circle + bold title + one-line explanation + optional issues list; confidence bar and number on officer screens only. Titles are user-facing; the code is the `VerificationStatus` enum.

| Code | Title | Icon / tint | Explanation pattern |
|------|-------|-------------|---------------------|
| pending | Queued for checking | clock / neutral | "The check will start shortly." |
| running | Checking document… | spinner / info + indeterminate bar | what is being compared |
| verified | Verified | check / success | what matched |
| issues_found | *n* issues found | triangle / error | one line + issue list (severity chip, message, evidence quote) + "What to do" |
| needs_review | Needs officer review | eye / warning | why (low confidence or suspicious content) |
| unreadable | Could not read this document | image / neutral | image or empty PDF; tip to upload PDF |
| failed | Check failed | x / error | invalid result; re-run available |
| unavailable | Check unavailable | ban / neutral | service not configured or timed out; you can still submit |

Every verification block on officer screens ends with an "Automated check · model · latency · advisory only" band so the AI is read as a checker, not a decider.

## Feedback lifecycle (as rendered)

Numbered circle (amber = open, blue = addressed, green = resolved) + target tag ("Section: Premises" / "Document: Tenancy agreement") + state badge + message + metadata line (author, round, date) + context line ("Changed: floor area 48 → 62", "Replaced: …renewed2027.pdf", "Resolved by you · 17 Sep"). Operator screens add a "Go to …" anchor button; officer screens add Edit/Withdraw (while under review, before release) or Mark resolved / View change.

## Iconography

Inline stroke SVG, 2 px stroke, 14–20 px. Used only where it carries meaning: navigation, status, actions, verification. No emoji, no decorative illustration.
