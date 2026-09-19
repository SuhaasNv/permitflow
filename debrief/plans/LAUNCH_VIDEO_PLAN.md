# PermitFlow launch video: final plan (rebuilt 19 Sep 2026 after the scratchpad was lost)

Consolidated state after fourteen revisions and four persona reviews (short-form creator, motion designer, product-video editor, hiring panel), all four at 9 or above. This file replaces the revision history that lived in the session scratchpad.

## Deliverable

- Landscape 1920 x 1080, about 25 s, 60 fps render, MP4 plus poster JPG baked as frame 0, share copy for Instagram and LinkedIn, SRT.
- Built as a HyperFrames composition (`/brag --voice` workflow), rendered locally.
- Desktop UI only, real product footage, no phone frames, no stock, no generated imagery.
- Posted only once v0.3.0 is live so permitflow.space answers; the repository is public (https://github.com/SuhaasNv/permitflow).

## Owner decisions on record

- Footage from the local stack with the real provider (`AI_PROVIDER=openai`, `gpt-4.1-mini`, key from the root `.env`); a second pass against production after v0.3.0 is a clip swap only.
- Voice on: Kokoro `af_heart`, speed 0.95 (chosen from five samples).
- Music: instrumental pop bed (see Audio).
- Story: the problem first, then the launch.
- The queue illustration was replaced by a plain-paper notification on the hiring panel's advice (Singapore licensing has been online through GoBusiness for years; a physical counter reads as not knowing the market). The owner may veto; the panel's least damaging form if kept: a hand sliding the slip across a plain counter edge, no line, no board, no clock, no clerk, captioned "How it feels", placed after the notification.

## Product truth (binding, verified in code)

- Operators never see evidence quotes or confidence (`backend/app/services/operator_view.py` strips `evidence`; `docs/design/USER_JOURNEY.md` step 7). The operator's check block says "Needs your attention" with "Some details do not match your form. Check them before you submit." (`frontend/src/features/operator/documents/VerificationBlock.tsx`). "Issues found", evidence and confidence appear only on the officer's case.
- "Addressed" happens only on Resubmit, never on replacing a file (`SCOPE.md` assumption 7).
- Labels verbatim: "New application", "Download licence (PDF)", "Ready to resubmit: 1 of 1 flagged item changed", "Route to Approval" (officer label for pending_approval).
- Licence number format `FEL-<year>-<six digits>` (`backend/app/domain/licence.py`). Application reference format `PF-<year>-<six digits>`; the old-way notification must not use it.
- Feedback template `certificate_expired`: "The food hygiene certificate you uploaded has expired. Please upload a certificate that is valid for the licence period." (`backend/app/domain/feedback_templates.py`).
- One person built it: "So I built PermitFlow."
- The state machine forbids Approve straight after Addressed: a site visit and Route to approval sit between.

## Story

Act one, the old way, on ink: three files whose names say everything (`application_v1.pdf`, `application_v2.pdf`, `application_v3_final(2).pdf`); a notification that names no section and no document; a slip with one word, "Resubmit."; a fourth file. Act two, the turn: "So I built PermitFlow." Act three, the loop working in the real product: the check finds the expired certificate before submission; the officer's feedback points at that document; only the flagged slot reopens; Verified, Resubmit, Addressed; site visit and route to approval; Approve; the licence. Closing line, the product's own: "Checks help you. Officers decide."

## Storyboard (times approximate; scenes 6 to 9 stretch to the rendered voice, scenes 1 to 5 keep their holds)

| # | Scene | Time | On screen | Voice |
|---|---|---|---|---|
| 1 | Three files | 0.0 to 1.4 | Ink ground. Three white cards (hairline `#dde1e7`, `--shadow-2` after landing), filename IBM Plex Mono 64 px, drop one per beat (about 0.5 s at 120 BPM): `application_v1.pdf`, `application_v2.pdf`, `application_v3_final(2).pdf`; frame 0 is already mid-drop; column centred at 42 to 45 % of frame height so the caption pill never overlaps | "Which one did the officer read?" (6) |
| 2 | The notification | 1.4 to 3.2 | Plain paper card, not the product's tokens (generic sans, `#f8f9fb`, no product hairline or radius): header "Ref. LIC/2026/000431", nothing else; under it the serif hook "Sent back by one word." (Instrument Serif); line 1's caption leaves at this cut | none |
| 3 | The slip | 3.2 to 5.0 | Hard cut, slip already full frame, same plain-paper rule: "Resubmit." (large, on screen by 3.45 s), then "Resubmission required. See attached.", then grey "No section named. No document named." | "It came back with one word: resubmit." (7) |
| 4 | The files, again | 5.0 to 6.8 | Hard cut, chips 1 to 3 at rest in their scene 1 pixels; a fourth drops at 5.2: `application_v3_final(3).pdf`; 0.6 s hold | "Which document? Which section? Everything, again." (6) |
| 5 | The turn | 6.8 to 8.2 | Ink. Brand tile (120 px) with its three lines rises (E16); only the check draws (320 ms); wordmark 72 px Public Sans 700 attaches from the mark's edge; on the beat the lockup travels and shrinks into the app header's own 28 px mark while the product page rises beneath it. No stroke-draw of the lines, no wipe | "So I built PermitFlow." (4) |
| 6 | The check | 8.2 to about 11.6 | Operator documents page, wide 400 ms, Punch onto the food hygiene certificate slot; cursor drops the PDF; the product's own 700 ms progress step once ("Checking your document", cut to under 0.9 s); warning Flip "Needs your attention", "Some details do not match your form." No evidence here | "The check finds an expired certificate before you submit." (9; captions "The check finds an expired certificate" / "before you submit.") |
| 7 | The officer | about 11.6 to 14.1 | Officer case page, wide 500 ms, Punch onto the header badge plus the rail; the check block "Issues found" with evidence "Valid until 3 January 2025" and confidence; the `certificate_expired` template card arrives inside the camera move; Flip "Pending Pre-Site Resubmission" | "Feedback points at the exact document." (6) |
| 8a | The fix | about 14.1 to 16.4 | Operator page in respond mode: three sections locked, one slot "Flagged"; cursor replaces the file; success Flip "Verified" with the check drawing inside the badge; release the Punch; banner "Ready to resubmit: 1 of 1 flagged item changed"; cursor presses Resubmit | "Only the flagged parts reopen." (5) |
| 8b | The rail | about 16.4 to 17.8 | Hard cut straight into the punched framing of the officer rail; the "Open" badge placed at the pixels the Resubmit button occupied; Flip "Addressed"; 0.9 s hold | none |
| 8c | Route | about 17.8 to 18.6 | Officer header badge Flip to info "Route to Approval" (site visit done, routed); caption as support only | none |
| 9 | The outcome | about 18.6 to 22.9 | Officer case, wide 400 ms; the Approve dialog opens with the product's `pf-dialog-in` (never pre-opened), note filled; cursor presses Approve on the beat; dialog leaves; success Flip "Approved" with the bell; Punch onto the licence card placed at 40 % frame height: "Licence FEL-2026-000012", "Download licence (PDF)"; 0.8 s later the serif closing line in the free lower third: "Checks help you. Officers decide."; 0.8 s hold | "Approval issues the licence. Every step on record." (8) then "Checks help you. Officers decide." (5) |
| 10 | End card | about 22.9 to 24.5 | 220 ms dissolve to ink (the film's only dissolve); lockup already assembled rises (E16); the fictional-service line first, 24 px metadata grey, bottom safe margin: "A fictional licensing service built for an engineering assessment. Not a government service."; then permitflow.space and github.com/SuhaasNv/permitflow, Public Sans 500 at 56 px, in their own band above it, legible at least 1.0 s; last frame on ink beside frame 0 on ink for the loop | none |

Fifty-six words of voice. Poster frame: the licence card settled, just before the closing line.

## Motion specification (the token sheet, built and locked before any scene)

| Token | Definition | Source |
|---|---|---|
| `pf` | ease cubic-bezier(0.2, 0, 0, 1) | `--ease-out` in `frontend/src/styles/index.css` |
| `pf-io` | ease cubic-bezier(0.4, 0, 0.2, 1) for anything leaving | `--ease-in-out`, `pf-toast-out` |
| E6 | opacity 0 to 1, y 6 to 0, 320 ms `pf`; E6-fast the same at 220 ms | `.pf-enter`, `.pf-enter-fast` |
| E16 | opacity 0 to 1, y 16 to 0, 640 ms `pf`; display-scale elements on any ground | the landing page reveal |
| Flip | badge tone change 220 ms: dot colour at T; pill background, border, text at T+40; old label out 150 ms and new label in 220 ms from T+60 on one left edge; success adds the product's `.pf-check` drawing inside the icon at T+120 over 320 ms | badge tone transition, `pf-draw` |
| Punch | 1.35x on one target, target-centred (outer wrapper scales, inner counter-translates), 640 ms in `pf`, 640 ms release `pf-io`, lower third kept clear, crop never past 88 % of the frame; wide hold 400 to 500 ms before it; content arrives inside the camera move, never before it | HyperFrames coordinate-target-zoom |
| Cursor | 24 px inside the world wrapper so it scales with the page; glide 240 ms under 150 px, 480 ms under 600 px, 640 ms beyond, `pf`; press y +2, 150 ms in, 150 ms out, with the target's pressed state; no ring, no ripple; rests 80 px from its next target; never leaves the frame | none in the product |
| Cuts | hard cuts everywhere, the incoming scene entering on its own token (E6 on white, E16 on ink); the one dissolve is scene 9 to 10 at 220 ms | dialog backdrop fade |
| Chip drop | the one exemption from the 6 px rise: y -48 to 0 over 320 ms `pf`, card opaque within 150 ms while still moving, filename E6 at +40, shadow fading in 150 ms after landing; chip 1 from y -40 at frame 0 | feed-scale legibility |
| Weight and overlap | chip solid before it lands; badge dot before label before check; caption text then pill at +40; the turn's tile settling while the check draws and the wordmark attaching at the check's completion | authored, not templated |

Refused: stroke-draw of the mark's three lines (`Logo.tsx` is static, only the check draws), page wipes, 600 ms crossfades, any push-in or drifting still, click ripples, overshoot, speed-ramped footage, count-ups, gradients, emoji, caps.

Staging: at every cut the eye lands where it left (chip column and board on one x; "Open" badge where the Resubmit button was; URL on the closing line's y; the officer scene's camera moves before the card arrives).

## Visual identity contract (from the code)

Source: `frontend/src/styles/index.css` and `fonts.css`; the code wins over `docs/design/DESIGN_SYSTEM.md` (`text-3` is `#616c7a`).

- Ink `#1b2430`; page `#f4f5f7`; surface `#ffffff`; surface 2 `#f8f9fb`; line `#dde1e7`, strong `#aeb6c2`; text `#1b2430`, `#465060`, `#616c7a`.
- Brand red `#a8192a` (hover `#8a1422`, soft `#fbedee`, line `#efb8be`): the mark and nothing else in this film.
- Tones with soft and line: success `#067647` / `#ecfdf3` / `#a6e9c4`; warning `#9a4a00` / `#fff6e5` / `#f5cf86`; error `#b42318` / `#fef3f2` / `#f4b7b1`; info `#175cd3` / `#eef4ff` / `#b2ccfa`; neutral `#475467` / `#f2f4f7` / `#d0d5dd`. Every pill keeps its 1 px line so it survives a projector.
- Band lights on ink: `#a8192a` and `#2c3a52`, blur 60 px, opacity 0.4, drift 18 s and 22 s (`.pf-band-glow`), breathing subtly with the music RMS; not a gradient.
- Radii 4 / 6 / 10 px, badges pill; `--shadow-2` for floating cards, `--shadow-3` for dialogs; flat panels no shadow.
- Fonts from the product's own woff2 files in `frontend/public/fonts/`, same `@font-face` as `fonts.css`, no Google Fonts: Public Sans variable 400 to 700 (UI, captions, wordmark 700); Instrument Serif 400 regular and italic (display lines only); IBM Plex Mono 400 and 500 (filenames, licence number).
- Badges on hero recreations at the 28 px large size. Nothing on ink moves less than 16 px. Nothing the viewer must read falls under 11 px at 0.2x (390 px wide).
- The old-way notification and slip use none of the product tokens (generic sans, plain paper) so the old way never wears PermitFlow's clothes.

QA: `hyperframes check` (contrast is a hard gate); a render frame beside a live screenshot of the same screen at 1920 wide, compared at 100 %; the contact sheet checked at 0.2x; render at 60 fps.

## Captions

- Public Sans 600, 68 px at 1080p (56 px cap height). Lower third, centred. Ink text on a white pill with the `#dde1e7` hairline on product scenes; white on an ink pill on ink scenes.
- One card per voice line, six words or fewer, verbatim; cut on the first spoken word, held until the next line; leaves at a cut into a scene with no voice. Text E6-fast at the word, pill 220 ms at T+40. No karaoke.
- None on the closing line (already on screen), the notification, the rail, the route beat, or the end card. Never over the punched element; clear of the serif hook's corner.
- SRT exported alongside.

## Audio

- Voice: Kokoro `af_heart` at 0.95 through `npx hyperframes tts`, one WAV per line, own track at 1.0; scene lengths derived from the WAVs.
- Music, decided 19 Sep: `notes/pitch/music/FINAL-launch-bed-cand-4-trim2.83.mp3` (HeyGen catalog track cand-4, 129.2 BPM, trimmed in at 2.83 s so a beat sits under frame 0 and the first downbeat lands at 0.46 s; the owner's ear pick, confirmed by the supervisor's measurements: steadiest grid of eight, -12.5 LUFS, LRA 3.1, no vocal evidence). With that trim the four locks fall at 6.79 / 9.85 / 15.47 / 22.50 s (max 0.15 s from a strong cue) and every cut within 0.23 s of a beat; the video's 24.5 s end sits before the track's fade. The detector's grid stops at 14.55 s (a softer-attack second section, not a breakdown); the grid is extended in phase, which `hyperframes beats` should confirm at composition. Fallback: cand-8 trimmed in at 7.52 s. Local MusicGen is not used again on this machine (the likely cause of the 19 Sep crash). The audible proof (track plus a tick at every snapped cut) is `FINAL-launch-bed-cand-4-trim2.83-proof.mp3`; the supervisor's full ranking is `music-ranking.md`.
- Bed at 0.30 between lines, ducked to 0.10 under every voice line, no drop under a claim, fades to silence over the end card. Never above 0.30. "If a viewer can hum it afterwards, it is too loud."
- Beat locks from the chosen track (`npx hyperframes beats` or the brag skill's `analyze_music_cues.py` via `uv`): the turn, "Needs your attention", "Verified", "Approved" plus the licence card, each within 0.15 s of a strong cue; every other cut snapped to the nearest beat within 0.10 s; chip spacing set to the beat interval. Proof before any video: the track with a tick at each snapped cut, listened to by the owner.
- SFX sparse, low high-frequency risk, from the brag skill's Kenney set: click on the drop and on Approve, soft impact on the first landing, drops on badge flips, one bell on the licence card; none in the problem act; never more than one per second; redundancy pass after the first assembly because the pop bed carries more of the motion. Each SFX on its own ascending track index.

## Launch copy

Instagram: "Which one did the officer read? PermitFlow keeps a licence application in one place: the check, the feedback, the fix, the licence. Checks help you. Officers decide. permitflow.space"

LinkedIn:
"A licence application comes back with one line: please resubmit. Which document? Which section? Everything, again.

PermitFlow is a licensing workflow I built in three days for an engineering assessment. An operator applies with checked uploads and an advisory AI reads each document before submission. The officer's feedback points at the exact section or document, only the flagged parts reopen, every revision is kept and every step is audited. Approval issues the licence.

Twenty-five seconds of it below. What to look for: the check landing on an expired certificate, the feedback tied to that document, and the resubmission that reopens one slot. The AI never decides; the officer does.

Code, tests, threat model and the honest list of what is not built: https://github.com/SuhaasNv/permitflow · permitflow.space"

No em dashes, no emoji, no hashtags, nothing the product does not do.

## Build order

1. Token sheet: the four helpers in a 4 s test, checked at 100 % and 0.2x; locked first.
2. Flip with the check draw: contact sheet at T, T+60, T+120, T+220.
3. The turn: measure the header lockup from a footage still; verify the landing pixel-exact.
4. Punch targets as constants; caption zone clear; end frames on a contact sheet.
5. Footage: scratch Playwright script (the `demo-video` recipe) against `vite preview` at 1920 x 1080, fresh browser per scene, real sign-in, demo PDFs from `docs/demo/documents` (`with_issues` then `clean`), live provider; the documents page scrolled so the slot sits in the upper half before capture; script stays outside the repository.
6. Problem act: chips and slip; frame 0 mid-motion checked at 0.2x.
7. Voice WAVs, then captions cut on the first spoken word.
8. Music chosen and beat-proofed; cut times snapped; SFX; the 220 ms end dissolve; the loop seam.
9. `hyperframes check`, `snapshot`, animation map for dead zones over 0.9 s, render at 60 fps, poster baked as frame 0, share copy, the owner watches at 1080p and at half size.

## Interview questions the panel would ask (prepare answers)

1. Assumption 13 returns 403 when an operator fixes a mistake in an unflagged section: what was weighed, what would change it.
2. Checks run in-process and a redeploy marks running checks failed: what the operator sees mid-deploy; queue or object storage first in production.
3. Two of 21 fairness runs failed and the harness was blamed: how one would know the model was wrong instead; what evidence before calling the verifier fair.
