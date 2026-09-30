# Legal, privacy and accessibility review

Story US-057, 19 September 2026. The owner's brief: a checklist of legal, privacy and accessibility items, with the instruction to say honestly what applies and to work carefully. This document takes every item on that checklist, says whether it applies to PermitFlow, what was done, and where the evidence is. Where an item does not apply, it says why rather than pretending it was done.

Written by an engineer, not a lawyer. It is a good-faith reading of the law as it applies to a demonstration; before any real deployment a Singapore-qualified adviser should review the policies and the transfer arrangements.

## The checklist, item by item

| # | Asked for | Applies? | Done | Evidence |
|---|-----------|----------|------|----------|
| 1 | Privacy policy page | Yes | `/privacy`: operator, "do not use real data", what is collected, why, transfers (OpenAI, LangSmith, Railway), browser storage, retention, security, rights, changes | `frontend/src/features/legal/content.ts`, `PolicyPage.tsx`, footer links on the landing page and in the app shell |
| 2 | Terms and conditions page | Yes | `/terms`: what PermitFlow is (fictional), acceptable use, checks are advisory, no warranty, no payments, IP, governing law (Singapore) | same files |
| 3 | Cookie policy | Yes, as a statement | `/cookies`: the service sets no cookies; session storage for the token, local storage for one preference; why no banner | same files; verified: no `document.cookie` anywhere, backend sets no `Set-Cookie` |
| 4 | Cookie consent banner | No | Not needed. Singapore's PDPA has no cookie-consent rule; the EU ePrivacy Directive (Art. 5(3)) exempts storage strictly necessary for a service the user requested, which is all this site uses. A banner would ask consent for nothing | `grep -rn "document.cookie\|Set-Cookie"` returns nothing; storage use listed in the cookie policy |
| 5 | Refund policy | No | Nothing is sold or charged. Stated in the terms so nobody looks for one | `/terms`, "Payments and refunds" |
| 6 | Form consent | Yes, as notification | PDPA works on notification of purpose plus consent by voluntary provision (s. 13 to 15, s. 20). Added a notice on the sign-in page and on the documents page saying it is a demonstration, not to upload real data, and where the data goes, each linking the privacy policy. The form's Declarations section already carries the inspection consent and the accuracy declaration. No new checkbox: the accounts are shared demonstration accounts, so a per-person consent record would be fiction | `LoginPage.tsx`, `DocumentsPage.tsx`, `backend/app/domain/form_schema.py` (declarations) |
| 7 | Only connect necessary data | Yes | The verifier receives only the document type, the extracted text (capped at 20,000 characters) and the matching form section (SEC-012); LangSmith receives the result and identifiers, never the inputs, by default (T21); no analytics, no third-party scripts | `THREAT_MODEL.md` T18, T21; `tests/unit/test_openai_wire.py`, `test_tracing.py` |
| 8 | Check analytics tracking | Yes | None exists. No Google Analytics, tag manager, Plausible, PostHog, Hotjar, Sentry or pixel; the only network calls from the browser are to our own API. Decision: keep it that way for the demonstration | `grep` over `frontend/index.html` and `src` for the usual names: nothing |
| 9 | Check third-party embeds | Yes | None: no iframes, no maps, no video, no social widgets. The one third-party request the site made, Google Fonts (which discloses the visitor's IP address to Google), is gone: the three typefaces are now served from our origin | `frontend/public/fonts/`, `src/styles/fonts.css`, `index.html`; `docker/nginx.conf.template` caches them |
| 10 | Make the site accessible | Yes | Automated gate: axe-core with the WCAG 2.0, 2.1 and 2.2 A and AA rules plus best practices on 14 screens at desktop width (5 public, 7 operator, 2 officer), the feedback composer and a confirmation dialog, and 7 screens at phone width (390 px, which brings in the WCAG 2.2 target-size rule): 23 states. v0.4.0 (US-088) added the appointment card and panel, the checklist as a draft and as submitted at 1024, 820 and 390, the respond page, the history with rounds, the four admin screens and the add-account dialog, a 44 px target measurement and a keyboard walk of the checklist. Findings fixed: missing `main` landmark on the landing and sign-in pages, content outside landmarks (app masthead, now a named region; the sign-in page's decorative column, now a named `aside`), a contrast failure (below), and no skip link anywhere (added) | `frontend/e2e/a11y.spec.ts`, run in CI's end-to-end job |
| 11 | Add alt text | Not applicable | The site has no `<img>` elements. Every SVG is decorative and carries `aria-hidden="true"`; the brand mark is inside a link whose accessible name is "PermitFlow home". The licence PDF's brand mark is drawn as vector paths, not an image | `grep -rn "<img" src` returns nothing; `Logo.tsx` |
| 12 | Check colour contrast | Yes | Every text token was computed against every surface token (WCAG relative luminance). `text-3` (#66717f) failed at 4.34:1 on `surface-3` and at 4.36:1 on `primary-soft`, contradicting the design system's claim of 4.5:1 everywhere. Changed to #616c7a: lowest pairing now 4.68:1 (`surface-3`); 5.34:1 on white. `line-strong` is a border colour, never text, so it is held to the 3:1 non-text ratio instead (WCAG 1.4.11): #aeb6c2 at 2.04:1 failed it and became #838c99 at 3.40:1 on 1 Oct 2026 (US-095, `tokens.test.ts`) | `src/styles/index.css`, `docs/04-design/DESIGN_SYSTEM.md`; the computation is reproduced in this document's appendix |
| 13 | Make forms keyboard-friendly | Yes | Sign-in completes from the keyboard alone (test); every control has a visible `:focus-visible` ring (2 px, 2 px offset, `info` blue at 5.99:1 on white); dialogs are native `<dialog>` elements opened with `showModal()`, so the browser traps focus inside, Escape closes (wired to the cancel action) and focus returns to the opener; focus lands on Cancel for destructive dialogs and on the primary action otherwise; the drop zone is a native file input with a visible label and focus ring, so Enter or Space opens the picker; a skip link to `#main` was added to the landing page, the policy pages and the app shell (missing before this story); radio groups, selects and checkboxes are native controls with labels; axe's `label`, `focus-order-semantics` and `tabindex` rules pass on every screen | `a11y.spec.ts` (keyboard sign-in, skip link); `Dialog.tsx`; `DropZone.tsx`; `index.css` `:focus-visible`, `.pf-skip-link` |
| 14 | Use clear button labels | Yes | Reviewed every button in the codebase: labels are verbs with objects ("Save and continue", "Request resubmission", "Mark site visit scheduled", "Download licence"), destructive ones name the consequence and require a note, icon-only buttons carry `aria-label` (notifications bell, show/hide password, close dialog). axe's `button-name` and `link-name` rules pass on every screen | `a11y.spec.ts`; `docs/04-design/UI_STATES.md` |
| 15 | Remove fake reviews | Not applicable | There are none: no testimonials, ratings, star widgets, customer logos or "trusted by" strip anywhere. The landing page describes the workflow and the documents needed, nothing else | `LandingPage.tsx` |
| 16 | Remove unsupported claims | Yes | Landing copy re-read line by line. Retained: process descriptions that the software does. The one claim that could mislead, that this is a licensing service, is countered in the footer of every public page ("A fictional licensing service built for an engineering assessment. Not a government service."), in the app shell ("Fictional assessment product"), in the terms, and on every demonstration document ("Fictional document produced for a software demonstration. Not issued by any authority"). "Secure licensing portal" in the app masthead is the only superlative; it describes a portal with Argon2, JWT, server-side authorisation and a published threat model, and stays | `LandingPage.tsx`, `AppShell.tsx`, `docs/12-demo/documents` |
| 17 | Add business details | Yes, as far as they exist | There is no business. The policies name the operator (Suhaas Nv), state it is a portfolio and assessment project, link the repository, and give the repository's issue tracker as the contact. No email address on the site, by the owner's choice (spam) | `/privacy` "Who operates this service", `/terms` |
| 18 | Check copyright on images | Yes | No raster images. The favicon and brand mark are original vector drawings by the owner. Fonts: Public Sans (U.S. General Services Administration), Instrument Serif, IBM Plex Mono (IBM), all SIL Open Font License 1.1, which permits bundling; notices kept with the files. Demonstration documents are the owner's own fictional creations. The source code carries no open-source licence, so all rights are reserved apart from viewing; the terms say so | `frontend/public/fonts/LICENSES.txt`, `/terms` "Intellectual property" |
| 19 | Check applicable local laws | Yes | Below | this document |
| 20 | Flag any other risks | Yes | Below | this document; `THREAT_MODEL.md` T22 |

## Laws considered

| Law | Relevance | Position |
|-----|-----------|----------|
| Personal Data Protection Act 2012 (Singapore), as amended 2020 | The service collects personal data (names, contact details, uploaded documents that can carry NRIC numbers) from people in Singapore. Obligations: consent (s. 13), purpose limitation (s. 18), notification (s. 20), access and correction (s. 21, 22), accuracy (s. 23), protection (s. 24), retention limitation (s. 25), transfer limitation (s. 26), breach notification (s. 26A to 26E), and the Do Not Call provisions (not engaged: no marketing messages) | Notification and purpose: the privacy policy and the two in-app notices. Protection: the threat model's controls. Access and correction: the policy explains the route. **Gaps, stated in the policy:** no retention schedule (data is kept until an environment reset; a production version would delete extracted text 90 days after a terminal state, SEC-012); transfers to OpenAI, LangSmith and Railway in the United States are not covered by contractual clauses that would satisfy s. 26 for a production service; no breach-notification procedure. For a demonstration whose users are told not to enter real personal data, these are disclosed rather than solved |
| Spam Control Act 2007 | Only if the service sent unsolicited commercial electronic messages | Not engaged: the service sends no email at all; notifications are in-app |
| Electronic Transactions Act 2010 | Electronic records and signatures; relevant if the demonstration licence were held out as a real instrument | Not engaged: the certificate says it is fictional and the terms forbid presenting it as real |
| Copyright Act 2021 | Fonts, images, demonstration documents, the code | Covered under item 18 |
| Misrepresentation and passing off (common law), Government agency impersonation | The strongest real risk for a fictional "licensing service": a visitor believing it is an agency | Mitigated by the disclaimers on every public page, the certificate and the documents; no agency name, crest or ".gov.sg" likeness is used; the registrar and institute on the documents are invented names with "fictional" printed on them |
| Computer Misuse Act 1993 | Applies to visitors, not the operator; relevant because the demonstration credentials are public | The terms forbid probing or bypassing authorisation; the threat model documents what the authorisation actually enforces |
| WCAG 2.2 AA (W3C), Singapore Digital Service Standards (government sites) | No statute obliges a private demonstration to meet WCAG; the government's own standard asks for WCAG 2.1 AA on public services. Adopted 2.2 AA as the bar because a licensing workflow is exactly the kind of service that must be usable by everyone | Automated gate in CI; manual keyboard walk; contrast recomputed |
| EU GDPR, UK GDPR, ePrivacy | Only if the service targeted people in the EU or UK. It does not: Singapore licence, Singapore addresses, no EU-language versions, no EU marketing. Incidental EU visitors do not bring the site into scope (Art. 3(2) requires targeting) | Not targeted. The cookie policy still explains the ePrivacy position because reviewers ask |

## Other risks flagged

1. **Public demonstration credentials with a live AI provider.** Anyone can sign in, upload a real document and have its text sent to OpenAI. Mitigation now: the notices and the policy; the 10 MB and type limits; no images are read. Better: a per-environment banner "demonstration data only" and an automatic reset of the development database on a schedule. Recorded as T22 in the threat model.
2. **Retention without a schedule.** Uploaded files, extracted text and audit rows live until a reset. A production version needs SEC-012 implemented and a documented reset cadence.
3. **Cross-border transfers.** OpenAI, LangSmith and Railway are in the United States. For a real deployment: a regional provider or a zero-retention agreement for the model, LangSmith APAC (the organisation's region is fixed at sign-up and this one is US), Railway's Singapore region for the database and the volume.
4. **NRIC numbers in uploaded certificates.** The demonstration certificate masks the NRIC (S****512A). A real food hygiene certificate would carry a full NRIC, which the PDPC's NRIC advisory guidelines say should not be collected unless required by law or necessary to verify identity to a high degree. A production version would redact NRIC patterns from extracted text before storage and before the model call.
5. **The demonstration licence looks official enough to misuse.** The certificate is a PDF with a number and a verification code and no digital signature. The terms forbid presenting it as real and the document says it is fictional; a production version would sign it (T20).
6. **Session token in `sessionStorage`.** Readable by any script on the page; there is none, and the CSP-adjacent headers are set, but a production version would move to an `httpOnly` cookie (T14). Noted here because the cookie policy's "no cookies" is a consequence of that choice, not a virtue of it.
7. **No open-source licence on the repository.** Reviewers can read it; nobody may reuse it. That is the owner's decision; if the intent is to share, add a licence file and update the terms.

## What was verified by hand, not only by tools

- Every public page and every app screen was opened at 1280 and 390 pixels after the changes: footer links present, policy pages readable, notices visible, nothing overflowing.
- Keyboard: skip link, Tab order on the sign-in page, the application form (all field kinds), the documents page (the drop zone's file input takes focus, Enter opens the picker), the feedback composer and the confirmation dialogs (focus inside the dialog, Escape closes, focus returns to the button that opened it).
- Accessible names read from the DOM: the notifications bell ("Notifications, n unread"), the password toggle ("Show password" / "Hide password"), the brand link ("PermitFlow home"), the status badges (label text, never colour alone), the skip link ("Skip to content").

## Appendix: contrast computation

WCAG 2.x relative luminance, ratio = (L1 + 0.05) / (L2 + 0.05). Text tokens against surface tokens after the change (before: `text-3` was #66717f, 4.34:1 on `surface-3`).

| Token | on surface (#ffffff) | on bg (#f4f5f7) | on surface-2 (#f8f9fb) | on surface-3 (#eef0f3) | on primary-soft (#fbedee) | on info-soft (#eef4ff) |
|-------|------|------|------|------|------|------|
| text #1b2430 | 15.65 | 14.35 | 14.86 | 13.71 | 13.75 | 14.18 |
| text-2 #465060 | 8.15 | 7.47 | 7.74 | 7.14 | 7.16 | 7.38 |
| text-3 #616c7a (new) | 5.34 | 4.89 | 5.07 | 4.68 | 4.69 | 4.83 |
| primary #a8192a | 7.40 | 6.78 | 7.03 | 6.48 | 6.50 | 6.70 |
| success #067647 | 5.69 | 5.22 | 5.40 | 4.98 | 5.00 | 5.15 |
| warning #9a4a00 | 6.26 | 5.74 | 5.94 | 5.48 | 5.50 | 5.67 |
| error #b42318 | 6.57 | 6.03 | 6.24 | 5.76 | 5.78 | 5.95 |
| info #175cd3 | 5.99 | 5.49 | 5.68 | 5.24 | 5.26 | 5.42 |

All at or above 4.5:1 (AA for normal text). Large text and UI components need 3:1; nothing relies on the lower bar.

### v0.4.0 pairings (recomputed 21 Sep 2026, US-088)

The new screens put text on the soft tone surfaces: the account-in-use block and the operator's counter-proposal on `warning-soft`, the Active and Protected chips on `success-soft`, the read-only banner on `neutral-soft`, the four `Alert` tones with their own darker text. Same computation.

| Token | on warning-soft (#fff6e5) | on success-soft (#ecfdf3) | on error-soft (#fef3f2) | on info-soft (#eef4ff) | on neutral-soft (#f2f4f7) |
|-------|------|------|------|------|------|
| text #1b2430 | 14.58 | 14.84 | 14.40 | 14.18 | 14.21 |
| text-2 #465060 | 7.59 | 7.73 | 7.50 | 7.38 | 7.40 |
| text-3 #616c7a | 4.97 | 5.06 | 4.91 | 4.83 | 4.84 |
| primary #a8192a | 6.90 | 7.02 | 6.81 | 6.70 | 6.72 |
| success #067647 | 5.30 | 5.40 | 5.23 | 5.15 | 5.16 |
| warning #9a4a00 | 5.83 | 5.94 | 5.76 | 5.67 | 5.68 |
| Alert warning text #6e3500 | 9.01 | | | | |
| Alert info text #0f3e8a | | | | 9.16 | |
| Alert error text #7a1a12 | | | 9.74 | | |
| Alert success text #04532f | | 8.72 | | | |

White on `primary` (every primary button, the take-over action) is 7.40:1. The lowest v0.4.0 pairing is `text-3` on `info-soft` at 4.83:1. `line-strong` (#aeb6c2, 2.04:1 on white) remains a border colour and never carries text or a state on its own: every status has a label beside its dot.

### Target size on the touch screens (US-088)

The root font size is 15 px, so the `h-10` control height is 37.5 px. Since 21 Sep 2026 every button, input and chip is at least 44 px tall below the desktop breakpoint (1280 px) and compact from it; the gate measures every control on the checklist (390, 820, 1024) and the respond page (390, 820) and fails below 44 x 44. Inline text links (breadcrumbs, the header's tab links) are exempt as WCAG 2.5.8 allows for links in running text; a checkbox is measured by the label that wraps it. A keyboard walk of the checklist (Space and Enter pick a result, Tab reaches the flag and the comment, the autosave follows) is part of the gate.

## WCAG 2.2 AA audit, criterion by criterion (US-095, 1 Oct 2026)

Run with the `wcag-audit` method on the local build (mock AI provider): the axe gate above plus axe at 768 px, reflow at 320 px and in phone landscape (34 checks), target size at 375 px, text spacing at 375 and 1280, 22 keyboard walks with a focus-indicator and focus-hidden probe at each stop, border contrast measured in the browser, form errors, sign-in, the dialog and the notifications menu; then checked again in Chrome. Twenty screens: the public pages and the 404, six operator, three officer, three admin. The first run found six failures; all six are fixed and the second run found none. This is not a conformance claim: axe finds about a third of real issues, and the screen-reader pass below is still to be done by a person.

| SC | Level | Verdict | Evidence |
|----|-------|---------|----------|
| 1.1.1 Non-text Content | A | Pass | No `<img>`; icons `aria-hidden`; axe `svg-img-alt`, `button-name` clean |
| 1.2.1 to 1.2.5 Time-based media | A, AA | N/A | No audio or video |
| 1.3.1 Info and Relationships | A | Pass (fixed) | Dashboard groups were labelled by ids with spaces, so `aria-labelledby` named nothing; now `useId` (`DashboardPage.tsx`) |
| 1.3.2 Meaningful Sequence | A | Pass | DOM order is reading order (accessibility snapshots) |
| 1.3.3 Sensory Characteristics | A | Needs a person | No shape or position instructions found; to be read through by a person |
| 1.3.4 Orientation | AA | Pass | 844 x 390 landscape reflows, no orientation lock |
| 1.3.5 Identify Input Purpose | AA | Pass (fixed) | Sign-in `email`, `current-password`; the applicant's `organization`, `name`, `email`, `tel` added (`SectionForm.tsx`) |
| 1.4.1 Use of Color | A | Pass | Every status is a label plus a dot (`StatusBadge`) |
| 1.4.2 Audio Control | A | N/A | No audio |
| 1.4.3 Contrast (Minimum) | AA | Pass | axe clean on every screen; its undecided cases computed by hand (primary button 7.40:1, `text-3` on `warning-soft` 4.97:1) |
| 1.4.4 Resize Text | AA | Pass (fixed 1 Oct, persona run) | Zoom allowed (viewport meta); reflow at 640 and 320 px. At 200% text on a desktop the side rail cut its labels to "Dashbo…" and a form button was clipped at 390 px; the labels now wrap and buttons grow (`Button.tsx`, `AppShell.tsx`); a gate test measures both |
| 1.4.5 Images of Text | AA | Pass | None |
| 1.4.10 Reflow | AA | Pass | 34 of 34 checks without horizontal scroll at 320 px |
| 1.4.11 Non-text Contrast | AA | Pass (fixed) | Input, select and checkbox borders were 2.04:1; now 3.40:1 on white, 3.12:1 on the page; focus ring 5.99:1 |
| 1.4.12 Text Spacing | AA | Pass | Override stylesheet at 375 and 1280, nothing clipped (checked in screenshots) |
| 1.4.13 Content on Hover or Focus | AA | Pass | No custom tooltips; the notifications menu closes on Escape and returns focus |
| 2.1.1 Keyboard | A | Pass | Keyboard walks; the checklist and sign-in keyboard tests |
| 2.1.2 No Keyboard Trap | A | Pass | No trap in 22 walks; native `<dialog>` |
| 2.1.4 Character Key Shortcuts | A | Pass | Only Escape is handled |
| 2.2.1 Timing Adjustable | A | Pass (fixed) | Five minutes before the 60-minute idle limit the strip warns and offers Stay signed in (one request keeps the session). The 8-hour token limit is not renewable, by the owner's decision for security (option B, 1 Oct 2026); it is announced 30 minutes ahead and the work is saved as the user goes |
| 2.2.2 Pause, Stop, Hide | A | Pass | The only motion is the pulsing dot while a check runs (seconds), off under reduced motion |
| 2.3.1 Three Flashes | A | Pass | Nothing flashes |
| 2.4.1 Bypass Blocks | A | Pass | Skip link on the shell, landing, policy and What's new pages; landmarks elsewhere |
| 2.4.2 Page Titled | A | Pass | A title per route (`router.tsx`, tested) |
| 2.4.3 Focus Order | A | Pass | No positive `tabindex`; dialogs focus Cancel or the primary action and return focus |
| 2.4.4 Link Purpose | A | Pass | axe `link-name`; link texts read through |
| 2.4.5 Multiple Ways | AA | Pass | Navigation, the queue search, dashboard and list links |
| 2.4.6 Headings and Labels | AA | Pass | One h1 per screen, descriptive labels |
| 2.4.7 Focus Visible | AA | Pass (fixed 1 Oct, persona run) | An indicator at every stop in a normal browser. In Windows High Contrast the soft shadow ring of the checklist result buttons and checkboxes was stripped and nothing replaced it; they now carry a transparent outline (`outline-hidden`), which High Contrast draws; a gate test compares the control focused and blurred with forced colours emulated |
| 2.4.11 Focus Not Obscured (Minimum) | AA | Pass (fixed) | The sticky header, tab bar and submit cards hid the focus 30 times in 60 presses on a phone and 9 on a desktop; `scroll-padding` now keeps it clear, and a gate test finds 0 (78 without the fix) |
| 2.5.1 Pointer Gestures | A | N/A | No multipoint or path gestures |
| 2.5.2 Pointer Cancellation | A | Pass | Actions fire on click |
| 2.5.3 Label in Name | A | Pass (fixed 1 Oct, persona run) | The first audit marked this Pass without testing it. The persona run found three misses: the bell showed "9+" but was named "Notifications, 352 unread"; the version link showed "v0.4.0-rc.2 New" but was named "Version 0.4.0-rc.2, what's new"; the logo showed "PermitFlow Licensing Services" but was named "PermitFlow home". Names now contain what is shown; a gate test checks every labelled control on six screens, and a unit test the bell |
| 2.5.4 Motion Actuation | A | N/A | No motion input |
| 2.5.7 Dragging Movements | AA | Pass | The drop zone is also a file picker |
| 2.5.8 Target Size (Minimum) | AA | Pass | Every target under 24 px is an inline link or spaced; Stay signed in is 24 px |
| 3.1.1 Language of Page | A | Pass | `<html lang="en">` |
| 3.1.2 Language of Parts | AA | N/A | English only |
| 3.2.1 On Focus | A | Pass | No change of context on focus |
| 3.2.2 On Input | A | Pass | No select or radio navigates |
| 3.2.3 Consistent Navigation | AA | Pass | One shell per role |
| 3.2.4 Consistent Identification | AA | Pass | Same labels and icons throughout |
| 3.2.6 Consistent Help | A | N/A | No help mechanism |
| 3.3.1 Error Identification | A | Pass | `aria-invalid`, error text via `aria-describedby`, an alert summary |
| 3.3.2 Labels or Instructions | A | Pass | Visible labels, required marked |
| 3.3.3 Error Suggestion | AA | Pass | Errors say what to do |
| 3.3.4 Error Prevention | AA | Pass | Review page and declarations before submit; destructive actions confirm |
| 3.3.7 Redundant Entry | A | Pass | Resubmissions arrive pre-filled |
| 3.3.8 Accessible Authentication (Minimum) | AA | Pass | Paste allowed, `autocomplete` set, no CAPTCHA |
| 4.1.2 Name, Role, Value | A | Pass (fixed) | A locked stepper step used `aria-label` on a plain span (ignored); it now says "locked" as screen-reader text (`Stepper.tsx`) |
| 4.1.3 Status Messages | AA | Pass | Toasts and the save indicator in live regions; the portal strip's status region is always present so a session warning is read out |

Still to be done by a person: 1.3.3, and a screen-reader pass (VoiceOver or NVDA) of sign-in with a wrong password, a section saved with an empty required field, and a checklist result (pressed, then "Saved").

### Correction and persona run (US-096, 1 Oct 2026)

The table above first said "0 failures of 55". That was premature: 2.5.3 had not been tested and 2.4.7 and 1.4.4 had only been tested for the default browser settings. Nine personas were then run on the same build, and each finding was fixed on `feat/us-096-persona-fixes` with a test that failed before the fix.

| Persona | Method | Result before | Result after |
|---------|--------|---------------|--------------|
| Keyboard only, motor | Tab-only sign-in, skip link in the signed-in shell at 375 and 1280, focus never hidden | Pass | Pass |
| Screen reader | Structure of eight screens: one h1, no skipped levels, landmarks, names of about 1,100 controls, duplicate ids, language, live regions | Pass (not listened to) | Pass (not listened to) |
| Low vision | 200% text at 1280, 320 px reflow, clipped text | Side rail labels cut off, form button clipped at 390 px | Labels wrap, buttons grow |
| Colour blind | Four simulated deficiencies and greyscale on the dashboard and the checklist | Pass | Pass |
| Windows High Contrast | Forced colours emulated; focused and blurred control compared | Result buttons and checkboxes showed no focus | Focus drawn |
| Motion sensitive | Running animations with and without reduced motion | Pass (0 looping animations with the preference on) | Pass |
| Cognitive, attention | Queue refresh while a link has focus (70 s), error copy grade (5 to 7), timeouts | Pass | Pass |
| Voice control | Label in name over six screens | Three misses | None |
| Deaf, hard of hearing | No audio or video | Not applicable | Not applicable |

Found on the way and fixed: on the operator dashboard at 1280 px the status badge covered the application reference and ran past the card edge (the card header now wraps). A sweep of every screen at seven widths then found more overflow, all fixed: the officer queue's action button fell out of its column at 1280 px and wider; the admin Users table was cut off at 768 and 1024 px and the Overview idle table at 768 px; status badges ran past their box on narrow screens; an issue code did not break at 320 px. Still to be done by a person: a listening pass with VoiceOver or NVDA, and the High Contrast result on a real Windows machine (Chromium's emulation is what the gate uses). Known and accepted: the phone stepper shortens its step names to fit six steps (the current step is named in the heading below it); 200% text on a 390 px phone with every rem-based size doubled scrolls sideways, which is stricter than a real zoom (it behaves like a 195 px screen).
