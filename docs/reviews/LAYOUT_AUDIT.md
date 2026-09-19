# Layout audit (19 Sep 2026)

A read-only audit agent drove every route as operator and officer at 390x844, 820x1180, 1440x900 (plus 1024x768 and 1280x800 for the officer screens), measured overflow, clipping, sticky elements, tap targets and console errors, and looked at the screenshots. Run after the phone-width hotfix (US-037). Findings are tracked as US-043 (layout) and US-044 (backend). Status column is updated as items ship.

Summary: 27 route states, no horizontal page overflow anywhere, bottom tab bar never covers content, side rail reaches the window bottom on every desktop page, no popover or dialog left the viewport.

## High

| # | Route | Width | Finding | Fix | Status |
|---|-------|-------|---------|-----|--------|
| H1 | /app/applications | 820, rail expanded | The `md:` five-column table needs 684 px but the card is 528 px: business column collapses to 0, header labels overprint, the row action sits outside the card | Keep the stacked card layout up to `lg` | done (US-043) |
| H2 | /officer/queue | 1280, rail expanded | The `xl:` six-column grid leaves 79 px for Business: names truncate to three letters at the most common laptop width | Six columns only from `2xl`; four columns through 1535 px | done (US-043) |
| H3 | /officer/applications/:id audit trail | 1024, rail expanded | Fixed 150/180 px columns in a 333 px column: message column one word per line, actor overprints the message | Stacked layout inside the case column; four columns only from `xl` | done (US-043) |

## Medium

| # | Route | Width | Finding | Fix | Status |
|---|-------|-------|---------|-----|--------|
| M1 | Officer case submission sheet | 1024 | 220 px label column leaves 38 px for values | `minmax(120px,220px)` label column | done (US-043) |
| M2 | Officer case review rail | 1024, 1440 | Sticky rail taller than the viewport: the feedback list and Add feedback are off-screen until the page bottom | `max-h-[calc(100vh-88px)] overflow-y-auto` on the aside | done (US-043) |
| M3 | Officer case | 390, 820 | Review actions render after the whole submission and audit trail: the primary action is the last thing on the page | Review card first below `lg` | done (US-043) |
| M4 | Form stepper | 390 | Six labels run into each other; `truncate` never applies because grid cells have `min-width:auto` | `min-w-0` on each step | done (US-043) |
| M5 | Review page alert | 390 | Alert action beside the body leaves 160 px for text | Action wraps under the text on phones | done (US-043) |
| M6 | Audit trail | 820 | Same fixed columns leave 90 px for the message | Same as H3 | done (US-043) |
| M7 | Many screens | 390 | Tap targets under 40 px: filter chips, `size="sm"` buttons, breadcrumb links, Completion card links, feedback actions, checkboxes | 40 px minimum hit area below `sm` | done (US-043) |
| M8 | Feedback cards in the rail | 820 to 1440 | Meta and actions on one line: "Mark resolved" breaks into two lines beside Withdraw | Actions on their own row (shipped with US-039) | done (US-039) |

## Low

| # | Route | Finding | Fix | Status |
|---|-------|---------|-----|--------|
| L1 | Officer case | Applicant email truncated without a title | `title` attribute | done (US-043) |
| L2 | Review page | Filename `break-all` splits "cert.txt" mid-word | `break-words` | done (US-043) |
| L3 | Officer case revision history | "Revision 1" wraps at 390 | `whitespace-nowrap` | done (US-043) |
| L4 | Check result meta | Dangling "·" at line start when wrapping | Separator inside a nowrap span | done (US-043) |
| L5 | Search box | Placeholder cut at the input edge | Shorter placeholder, long text stays the accessible name | done (US-043) |
| L6 | Audit trail at 1440 | Type column narrower than `verification.completed` | Wider columns | done (US-043) |
| L7 | Drop zone copy | "business profile (acra)" lowercases the acronym | Use the label as-is | done (US-043) |
| L8 | Submitted page | Decided applications still read "Changes resubmitted" | Copy from the current status | done (US-043) |
| L9 | Landing and login | Header and footer links under 40 px on phones | Padding | done (US-043) |
| L10 | Officer case header facts | Four columns wrap at 1024 | Two columns at `lg`, four at `xl` | done (US-043) |

## Backend observation

Under 150 concurrent requests, 36 returned HTTP 500 after about 35 s with no `Access-Control-Allow-Origin` header: the generic exception handler runs in Starlette's `ServerErrorMiddleware`, outside `CORSMiddleware`, so the browser reports "could not reach the server" instead of "something went wrong, quote request id". The default engine pool (5 + 10, 30 s timeout) is the limiting factor. Tracked as US-044: larger pool, and unhandled errors answered inside the CORS layer. Open.

## Re-measured after US-043 (19 Sep)

Applications at 820 with the rail expanded: rows end inside the card (stacked layout until `lg`). Queue at 1280: no clipped text (six columns from `2xl`). Case at 1024 with the rail expanded: labels stack above values at `lg`, evidence quotes wrap, audit trail stacked until `xl`, review rail scrolls inside the viewport (664 px in 768). Case at 390: review actions render first. Stepper at 390: no clipped labels. Also from user feedback in the same story: secondary and ghost buttons lost the hover sweep, the Review card keeps its bottom padding when there are no actions, the Document checks stats have no underlines, and the site visit steps carry a note that they change the status only.

## Not reachable during the audit

The resubmit dialog (no released feedback on the sample application at the time) and the withdraw dialog (shipped after the audit started). Both were verified by hand in the stories that built them.
