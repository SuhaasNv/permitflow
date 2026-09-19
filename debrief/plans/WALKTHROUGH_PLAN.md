# PermitFlow walkthrough: final plan (rebuilt 19 Sep 2026 after the scratchpad was lost)

About 5:55, narrated, landscape 1920 x 1080, desktop UI only. Audience: the hiring panel first, LinkedIn second. Four persona reviews (editor, motion designer, hiring panel, plus the creator's caption rules), all at 9 or above. Shares the launch video's tokens, fonts, captions, voice and music (`LAUNCH_VIDEO_PLAN.md`).

## Pipeline

- Footage: the `demo-video` skill's Playwright recipe (`~/.claude/skills/demo-video`), driven by a scratch script outside the repository: `vite preview` build (never the dev server), 1920 x 1080 headless, one fresh Chromium per scene, real sign-in, demo PDFs via `setInputFiles`, readiness by `waitForFunction` markers, per-clip trim; overlays are not baked (captions come from assembly). Live provider (`AI_PROVIDER=openai`).
- Voice: Kokoro `af_heart` at 0.95; `narration.md` with one cue per sentence group written before filming for everything that does not depend on the model's answer; the sentences about the check result written from the actual take without quoting the model.
- Assembly: HyperFrames `general-video` composition: section cards, clips with trims, captions and SRT through `media-use`, the pop bed, cut labels; `check`, `snapshot`, render.
- Timing rule (from `claude-video-generator`): narration length sets every hold; a clip never advances mid-sentence; clips do not stretch, so each is at least narration plus 1 s with the last frame frozen when short.

## Opening (0:00 to 0:15)

| Time | On screen | Voice |
|---|---|---|
| 0:00 | Title card on ink: the launch video's turn (tile E16, check draws, wordmark); subline "A fictional licensing service built for an engineering assessment. Not a government service." in metadata grey; chapter number; 3 s, then footage while the line finishes | "PermitFlow. One application, from draft to licence, with every step on record." |
| 0:03 | Operator's documents page with the result already landed (no wait, no label, no live-model dependency in the opening), punched in on the certificate slot: "Needs your attention", "Some details do not match your form." | "The check caught an expired certificate before submission." |
| 0:08 | Punch out: four slots, three Verified, one needing attention; the progress indicator | "Before any officer looked. This is the operator's view; the officer sees more." |
| 0:13 | Hard cut to the operator dashboard | "Here is the whole loop, from a new application to the licence." |

## Structure (14 scenes, about 800 words at 150 words per minute)

| # | Scene | Start | Words | What happens |
|---|---|---|---|---|
| 1 | Title and the catch | 0:00 | 45 | as above |
| 2 | Operator: new application, one section | 0:15 | 55 | dashboard, "New application", the Business section: first field typed live, then a cut to the filled section, labelled |
| 3 | Documents, live checks, submit | 0:40 | 95 | one PDF per slot (one slot per type); the three clean ones dropped back to back while earlier checks run (one label between them); then the certificate with the planted expiry, the only live landing in the film (its own label); progress indicator; Submit; Submitted page held 2 s |
| 4 | Officer (section card): case, evidence, feedback, request resubmission | 1:25 | 115 | queue, Start review, the check block "Issues found" with the evidence quote and confidence, the `certificate_expired` template, Request resubmission, the badge flips |
| 5 | Operator (section card): respond mode, resubmit | 2:15 | 80 | notification, feedback on top, three sections locked (held 2 s), one slot Flagged, replace, Verified, "Ready to resubmit: 1 of 1 flagged item changed", Resubmit |
| 6a | Officer (section card): the resubmission | 2:50 | 60 | Start review again (required after a resubmission before Mark resolved), Changed marker, Compare Revision 1 and 2, Addressed then Resolved |
| 6b | Officer: site visit and decision | 3:20 | 55 | site visit as jump cuts, Route to approval, the officer's watermarked licence preview (confirm it renders headless, else capture headed), Approve with a note, the licence card held 2.5 s (poster) |
| 7 | Operator: outcome | 3:50 | 30 | Approved panel, "Download licence (PDF)"; the card, never the document |
| 8 | Audit trail | 4:02 | 45 | stepped scroll through the events, punch in on one row |
| 9 | The boundary | 4:20 | 25 | 15 s: the operator pastes an officer URL: "Not available for your role" (`frontend/src/features/shared/states.tsx`); the API answers 403, one line |
| 10 | The engineering | 4:35 | 60 | document captures, not screen recordings: the real files in a light paper viewer with the path in the header, pre-scrolled, no cursor: `domain/workflow.py`'s transition table, `tests/unit/test_workflow.py`'s exhaustive test, a green pytest summary, the CI run with the six AI-gate jobs; one Punch per capture on the row the voice names, landing on the noun; 5 to 6 s each, hard cuts; curated by deletion only; music silent |
| 11 | AI assurance: the fairness story | 5:00 | 60 | 21 name-swapped runs; the first run failed 2 of 21; the cause was the harness (the baseline email and director line left in the form), fixed, 21 of 21 twice; the question a regulator would ask, said plainly; music silent |
| 12 | Scope and the gaps | 5:25 | 55 | one section card: built (UC1 and UC2, the 14-state lifecycle), deferred (UC3 site-visit checklist), simplified (email mocked, in-process AI checks, local-disk files, JWT in sessionStorage, a Content-Security-Policy that still allows inline styles), the admin role reserved; three next steps |
| 13 | Close | 5:48 | 12 | 220 ms dissolve to ink; lockup E16; "Checks help you. Officers decide." E16 at +40; permitflow.space and the repository URL E6 at +500; 2 s hold while the bed fades; no fade to black |

Cut on purpose: a cover slide, a problem slide, a cold open on the officer's page, "three PDFs at once", the certificate document as a still, any push on a still, the re-run check, full-length status clicks.

## Motion vocabulary (tokens identical to the launch video)

| Element | Treatment | Duration, ease |
|---|---|---|
| Punch-in | 1.35x on the one element that changes, target-centred, cursor stays in frame, lower third clear | 640 ms `pf` |
| Punch-out | release before every cut and before the cursor travels outside the crop; never cut while zoomed | 640 ms `pf-io` |
| Cuts | hard cuts inside a role, incoming clip E6; a section card only at a role switch (title, Officer, Operator, Officer) and for the scope card; into an ink card a 220 ms dissolve, out of it a hard cut with E6 | 320 / 220 ms |
| Section card | full ink with the band-light drift; chapter number IBM Plex Mono 22 px E6, title Instrument Serif 72 px E16 at +40, subline Public Sans 22 px `#dde1e7` E16 at +80; mark 24 px top left; red only on the title card's mark; at most 3 s on screen, narration runs over the incoming footage | 320 / 640 ms |
| Title and close | the launch video's turn | as the launch |
| Holds | Submitted page 2 s, locked rail 2 s, licence card 2.5 s | static, on purpose |
| Scene 9 | notice page E6; Punch onto "Not available for your role"; the 403 line as a mono card (`#f8f9fb`, hairline, IBM Plex Mono 22 px, "403" in `#b42318`) E6 on the spoken "403"; release before the cut | 320 / 640 ms |
| Scene 10 | each capture E6; one Punch onto the named row on the narration's noun; release before the hard cut; no stagger, no cursor | 320 / 640 ms |
| Scene 11 | a mono row of 21 run glyphs on ink, E6 with the product's capped stagger (0, 40, 80, 120, 160, then 200 ms); the two failed glyphs Flip to error tone 60 ms after the row settles; the cause line E16 on the stressed word; two clean rows, all success tone; the regulator's question in Instrument Serif E16 | 320 / 640 ms |
| Scene 12 | a section card with the stagger on its three columns, 40 ms per item, capped | 320 ms |

Refused: a crossfaded open, a glowing logo, a punch on every click, icon boxes with arrows, a roadmap timeline, a decorative rule or a large "01" over a thin line, any drifting still, any count-up, any speed ramp.

## Cursor rules

- The launch Cursor token: 24 px inside the world wrapper; glide 240 ms under 150 px (form-field hops), 480 ms under 600 px, 640 ms beyond, `pf` ease; never a fixed 700 ms.
- Pause before a click 300 to 450 ms; 700 ms only before Submit, Request resubmission, Resubmit, Approve.
- Press y +2, 150 ms in and out, with the target's pressed state held 220 ms on the four decision clicks; no ring, no ripple.
- Move the real mouse with the fake one (`page.mouse.move`, `steps: 20`) so hover states play.
- Inject with `addInitScript` after `DOMContentLoaded`; each clip starts where the previous ended; never a cursor popping in at centre.
- During any hold over 2 s, glide to the bottom margin or off the right edge; never park on the punched element.

## Waits: cut and label, never ramp

| Wait | Treatment |
|---|---|
| Sign-in, route loads | trim to the readiness marker; never speed up a skeleton |
| Typing a section | first field live, cut to the filled section, labelled |
| Each upload's check (4 to 12 s plus the 2 s poll) | hold 1 s on the running state, cut to the result, labelled; scene 3 carries two labels in total |
| The certificate check and its replacement (scenes 3 and 5) | same; narrated once; if a live check runs past 15 s, hold 1 s and crossfade to the result |
| Site visit scheduled, done, route to approval | jump cuts, unmarked; the narration names them |
| Approve (certificate rendered in the transaction) | trim the pending frames |
| The certificate PDF | not shown; the watermarked preview before and the licence card after |

The label: IBM Plex Mono 22 px in `#616c7a` at the right of the caption pill, numbers first, "Check 14 s · 12 s cut", E6-fast, held through the cut; no clock, no icon. Each cut lands on a stressed narration word or a cursor move, never in silence. Cut points come from `waitForFunction`, never from elapsed time.

## Captions and labels

- The launch caption card built exactly the same (Public Sans 600; ink on a white pill with the hairline on footage; white on an ink pill on ink cards; text E6-fast at the first spoken word, pill at T+40; lower third; never over the punched element), sized for a laptop: 44 px, two lines at most, one card per sentence, verbatim from the WAV. Checked at 1280 px and 0.5x; the 0.2x feed test does not apply here.
- Role label "Officer" or "Operator" at the left of the pill, Public Sans 600 at 22 px; the cut label at the right; none on section cards.
- SRT exported for LinkedIn.

## Music

Decided 19 Sep: `notes/pitch/music/FINAL-walkthrough-bed-cand-1-loop.mp3` (HeyGen catalog track cand-1, 139.7 BPM detected but a half-time 70 feel, the owner's other ear pick; looped 0.44 to 24.49 s, 14 bars, with a 40 ms crossfade at the seam). A different track from the launch on purpose so the two films do not share one 24 s loop. 0.10 under narration, 0.22 on section cards and the close, silent under scenes 10 and 11; instrumental; no drop under a claim. Watch for the 8th-note pulse turning into ticking under the duck; if it does, fall back to cand-4 looped 1.43 to 23.73 s.

## Biggest risk and the mitigation

The live model and the advancing backend: later scenes depend on scene 3's check returning the intended result, and every officer click advances state, so a retake of scene 5 would mean refilming scenes 2 to 4. Mitigation: film scene 3 first as the proof of concept and keep the take that matches the demo PDFs' intent; film in journey order against one backend with a `pg_dump` at each scene boundary so any scene can be retaken alone; clips never stretch (narration plus 1 s minimum, last frame frozen when short).

## Build order

1. Voice confirmed (`af_heart`).
2. Scene 3 proof of concept (the live check) on a contact sheet and played by the owner; sets the tone (cursor, punch, caption card).
3. Remaining scenes in journey order with database dumps between them; the officer's watermarked preview checked headless.
4. `narration.md` finalised from the takes; WAVs; scene lengths derived.
5. HyperFrames assembly: cards, clips, captions, bed, cut labels, document captures for scene 10.
6. `check`, `snapshot`, a frame at every cut inspected, audio overlap count zero, full-text leak sweep of the recordings (emails, ids), render at 60 fps, the owner plays it end to end.
