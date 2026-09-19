# Iterations log: PermitFlow pitch deck

Two versions, one source of truth for the copy and speaker notes (`content.json`). The HTML slideshow lives in `html/`, the PowerPoint in `pptx/`.

## Assets used (and where they came from)

| Asset | Source | Used in |
|-------|--------|---------|
| Fonts (Public Sans variable, Instrument Serif, IBM Plex Mono, latin woff2) | `frontend/public/fonts/` (same files as `notes/pitch/launch/composition/assets/fonts/`) | `html/assets/fonts/`; converted to static TTF instances in `pptx/fonts/` for machines without the fonts |
| Brand mark | `docs/design/brand/permitflow-mark.svg` | `html/assets/brand/`; rasterised to `pptx/build/mark.png` |
| Colour tokens, ease and durations | `frontend/src/styles/index.css`; motion helpers copied from `notes/pitch/launch/composition/index.html` ("Tokens (Revision 6)": `pf` ease, e6, e16, glows) | both |
| Product screenshots, 1440 x 900 at 2x, dev.permitflow.space, 19 Sep 2026 | fresh Playwright captures of application PF-2026-001009 (seeded on dev through the API with the demo PDFs, two planted issues; never production) | `html/assets/screens/`; 16:9 crops in `pptx/build/` |
| Architecture PNG | `docs/architecture/permitflow-architecture.png` (copied, not placed: the slide draws a simplified diagram instead) | `html/assets/` |

The launch video's clips (`notes/pitch/launch/composition/assets/clips/*.mp4`) were inspected but not used: the fresh captures show the feedback round mid-flight (open items, findings with evidence), which the clips of PF-2026-001007 do not.

## Round 0 (build)

HTML: eleven scenes in one composition under one seekable root timeline (the `present` command in HyperFrames 0.8.50 serves the composition without the engine, so the deck follows the standalone-harness contract: self-managed scene visibility, posted scene manifest, imperative presenter-triggered builds on hold-point crossings, rest states baked into the timeline so `check` and `snapshot` see correct frames). `npx hyperframes check`: 0 errors after fixing six overlap findings (flip-card faces, marked as intentional layering), a canvas overflow on slide 4 (grid resized) and seven contrast warnings on the closing chain (arrows lightened to the muted token, lit state baked). One warning accepted: `composition_file_too_large` (a slideshow is one file by contract).

PowerPoint: pptxgenjs from `content.json`, LAYOUT_WIDE, 1920 x 1080 design grid; OOXML post-processing adds one Fade transition per slide and click-triggered Fade builds (320 ms, presenter-triggered only) on slides 2 (2 clicks), 3 (4), 4 (1), 6 (6), 7 (2), 9 (2). `validate.py`: all validations passed. Fixes before review: inline flows on slide 3 wrapped past the band (arrow now travels with the item it precedes, bands taller), tier bullets overflowed on slide 5 (type reduced, boxes taller), the Cambria title on slide 9 collided with the figures line (title box given two lines), Railway box on slide 8 widened.

Text parity check (`content.json` against the HTML and the pptx text dump): every copy string present in both; notes identical; no em dash. Known structural differences: eyebrows are upper-cased in the pptx; the pptx status swap on slide 6 starts at "Pending Pre-Site Resubmission" (the HTML shows "Under Review" first); the pptx slide 4 zoom is a click build rather than a fragment.

## Round 1

Scores before the fixes: hiring-panel reviewer HTML 6 / 10, PowerPoint 7 / 10; presentation-design reviewer HTML 6 / 10, PowerPoint 7 / 10.

### Applied (content, both versions, via `content.json`)

- Slide 9 Deferred: use case 3 has three post-site statuses, not two (`backend/app/domain/workflow.py`, `docs/reviews/PRODUCTION_READINESS_REVIEW.md` row 1).
- Slide 7 card 3 source: US-014 was the progress indicator; now `US-017 · US-018 · domain/editability.py`.
- Slide 5: the officer card shows confidence and model; the prompt version lives in the audit event and the trace (`CheckResult.tsx`, `services/verification.py`). Officer label is "Needs your review". The operator strip now says what the operator does see (outcome, explanation, each issue in plain words) and what it never sees (evidence quote, confidence), per `VerificationBlock.tsx` and `operator_view.py`.
- Slide 8: with no key the provider is `None` and the run is stored `unavailable`; the mock is the default and the test provider (`infra/ai/factory.py`). Production is run by hand from `main` and pauses for an approval (README "Deployment", CHANGELOG v0.3.0). Eyebrow "Designed for production" became "Built to be taken to production". Footer cut to "docs/architecture · 12 ADRs".
- Slide 6: station 5 gains Start review (a site visit is only reachable from Under Review); the sub-lines of the two replaced documents change to "Replaced in Revision 2 · file" on the same click as the badge; "Officer labels shown" moved to a footnote that also says the clean business profile was uploaded, so two of the set's three planted issues are in play; clicks 1 and 2 merged (Revision 1 and its findings), five clicks in total.
- Slide 7 title: "each enforced by code or a test"; the notes carry the FINAL_REVIEW admission that no single test is named for "the verifier never changes a status".
- Slide 3 footer: "Every dark or outlined chip is a control label in the product"; Compare revisions (a section heading) and Template (a select label) are plain text; Approve is a primary chip in both versions.
- Slide 2 footer: "Source: the assessment brief" (the file path moved to the notes); the notes no longer comment on the deck itself.
- Slide 4 headline is a claim: "The product runs one workflow for two personas and keeps every step traceable."; notes date the captures (19 September 2026).
- Slide 9: "70 stories, 4 deferred"; delivery wording; a fourth scope box "Built with AI tools, checked by hand" (Claude Code under CLAUDE.md rules, every diff read, tests per story, AI_USAGE.md) and a matching paragraph in the notes, so the panel's "what did you write?" is pre-empted.
- Slide 10: title says the order is the README's with severity from the readiness review; the two High items missing from the list added (Identity; Data protection, T18); ten items.

### Applied (HTML)

Real 500 / 600 / 700 Public Sans instances instead of synthesised bold; glow discs removed from the cover and closing (gradient and second red); cover screenshot cropped to lose the product footer and labelled "Officer"; slide number moved to the top right, clear of the presenter capsule; footers never touch content (slides 3, 5, 8); slide 4 grid 640 x 360 with standard top padding and the zoom as a cropped evidence band with a flat caption line; slide 5 columns aligned (same heading size, subtitle on every column); slide 6 sub-line swap and tighter vertical rhythm; slide 7 rebuilt as a two-column list with hairline rules, no numerals, fade-up in two groups (the 3D flip is gone); slide 8 lane height reduced; slide 9 figures row resized, checks leading; slide 10 ten items, no build; slide 11 arrows travel with their words, chain centred; type floor raised (station text, box subtitles, lane labels, role tags at 20 to 21 px, muted lines moved from text-3 to text-2). `check`: 0 errors.

### Applied (PowerPoint)

Chain boxes sized from the column (no overlap, inside the margin) and the loop drawn as a rounded outline behind them; slide 3 rows hand-wrapped (`br` tokens in `content.json`), arrows never open a line; slide 4 grid at the standard top with wrapping captions, the zoom as a click build showing the same evidence band; slide 5 operator strip from `content.json`; slide 6 station titles in a fixed two-line box, station actions as chips, sub-lines in sans with only the code in mono, the swap for the sub-lines, the footnote; slide 7 as the same two-column list; slide 8 lane gutter; slide 9 figures in the body font with bold numbers, four scope boxes, two-line headline box; slide 10 five rows; slide 11 chain centred. `validate.py`: passed for both files.

### Rejected, with reasons

- A twelfth slide on AI usage (hiring reviewer 15): the owner fixed the deck at eleven slides. Folded into slide 9 (fourth scope box) and its notes instead.
- Rewriting the closing headline as a verb sentence (design reviewer 19, slide 11): the closing line is the owner's wording from the plan; kept. The slide 4 headline was changed.
- Rendering slides 5, 6 and 7 as reproductions of the product's own components (design reviewer, "templated" section): the product is shown in its own screenshots on slides 4 and 6; reproducing components would cost more than the round allows and risks drifting from the real UI.
- "96% and 80.6%" without the space (hiring reviewer 25): the README and CHANGELOG write "96 %"; kept for consistency with the repository.
- Merging clicks 5 and 6 on slide 6 (design reviewer 26): the change from "Addressed in Revision 2" to "Resolved" is the point of the slide; kept as two beats. Clicks 1 and 2 were merged.
- Treating "Browse files" as not a control (hiring reviewer 10): it is the click target that opens the file picker; kept as a chip, and the footer now says "control label" rather than "button".
- Dropping the build on slide 7 (design reviewer 26): kept as two fade groups, which is the plan's intent; the numerals that made the first state look unfinished are gone.

## Round 2

Scores before the fixes: hiring-panel reviewer HTML 7 / 10, PowerPoint 6 / 10; presentation-design reviewer HTML 7.5 / 10, PowerPoint 6.5 / 10.

### Applied (content, both versions)

- Slide 3 band 4 now follows the state machine: Mark site visit scheduled, Mark site visit done, Route to approval, Approve.
- Slide 10 title: "the README's list plus the readiness review's High items"; backups with a tested restore (High) named in item 09; notes say three High items.
- Slide 5: one label everywhere ("Needs your review"); the fourth column's subtitle is in `content.json`.
- Slide 6 feedback row 2 quotes the officer's real sentence from the record.
- Slide 7 notes: the system actor is the use case 3 checklist auto-transition, not the verifier.
- Slide 2 notes: duplicate file reference removed.
- Click rhythm: the first content group now appears with the headline on slides 2, 3, 5 and 7 (no title-only beat); the notes' "[Next]" cues were re-counted and match both versions: 0, 1, 3, 1, 2, 5, 1, 3, 2, 0, 1.

### Applied (HTML)

Slide 6 swap wiring corrected (Addressed in Revision 2 and Pre-Site Resubmitted on click 4, Resolved and Site Visit Scheduled on click 5); station titles in a fixed two-line box; footnote 20 px; non-breaking "Revision 2" and "#01-12". Slide 5 cards size to content with the operator strip clear below them. Slide 9 figures row inside the margin. Slide 7 fills column-first so the first group is the left column. Slide 4 zoom crops to the evidence band from the Tenancy agreement row (no empty sidebar, no floor-plan sentence), slide number kept. Slide 3 bands regenerated from `content.json` with the same row breaks as the PowerPoint, arrows travel with their items. Slide 11 chain spread to the margins. Cover screenshot at 10 percent. Outside boxes on slide 8 solid, not dashed. `check`: 0 errors; 30 hold points captured at 1280 x 720, finals at 1440 x 900 and 1920 x 1080.

### Applied (PowerPoint)

Slide 2 loop hidden behind the box row (no ticks between boxes), friction rows spaced. Slide 4 rows spaced so captions never touch the next screenshot. Slide 5 equal heading sizes, Re-run check in bold. Slide 6 business facts in fixed columns, station chips sized to fit their column, feedback rows with room for the two-line sentence. Slide 7 as one flowing text box per principle (source line follows the body), column-first. Slide 8 lane labels and sub-lines at 19 to 20 px, solid outside boxes. Slide 9 scope boxes at 20 px with room for the fourth. Slide 10 row height for three-line items. `validate.py`: passed for both files; handout PDF and PNGs regenerated.

### Rejected, with reasons

- Adding click builds to PowerPoint slides 5, 8 and 11 (hiring reviewer 8): the owner's list of build slides is 2, 3, 6, 7 and 9 (plus the zoom on 4); the pptx notes strip "[Next]" on slides without builds at build time (`notes()` in `build.cjs`), which the reviewer had read from `content.json` rather than from the file. Verified with `markitdown`.
- Embedding fonts in the .pptx (design reviewer 26): PowerPoint's `.fntdata` embedding is not something pptxgenjs or a safe post-process can write; the TTFs ship in `pptx/fonts/` with an install note and a safe-font copy of the deck is provided.
- Chips inside slide 5 bullets in PowerPoint (design 21, hiring 17): a chip cannot sit inside a bulleted paragraph; the label is bold instead.
- Rebuilding slides 5 and 7 from the product's own components (design "generic" section): as in round 1, not attempted within the rounds available.
- "Officer's note:" prefix on slide 6 row 2 (hiring 15): the real sentence is now quoted instead.

## Owner review (19 Sep, 19:50 SGT), applied directly, no further reviewer round

- One click per animated slide: the former click numbers became a timed sequence inside a single click (600 ms between former clicks, 100 ms stagger inside), so slides 2, 3, 4, 6, 7 and 9 each need one click to enter and one click to reveal everything.
- Cover screenshot less transparent (78 instead of 90).
- File and ADR references removed from the slides: solution foot, AI foot ("Advisory by design: the check informs the officer and never decides"), principle cards without source lines, architecture boxes without ADR mentions and no foot, quality without the ADR figure and without the Implemented / Deferred / Simplified block, next without the README foot.
- Copy trimmed: principles title "Six principles, each enforced by code."; quality title "Checked by tests, gates and a written record."; each quality check one clause; next title and items shortened; workflow foot shortened.
- Rebuilt both files and the PDF handout; slide PNGs regenerated. The HTML version was not changed in this pass (content.json is the source, so a rebuild of the HTML picks the same text up; its builds remain fragment based).
