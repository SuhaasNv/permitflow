# PermitFlow pitch deck: how to present it

Eleven slides, the same copy and speaker notes in both versions (`content.json` is the source of truth). Audience: the hiring panel. Nothing autoplays in either version; every build is a key press or a click.

In the repository: the PowerPoint version (this folder). The HTML slideshow and the generator live in the git-ignored workshop folder `notes/pitch/deck/` on the author's machine; section A below describes it for completeness.

## A. HTML slideshow (`html/`)

Present:

    cd notes/pitch/deck/html
    npx hyperframes@0.8.50 present .          # or: npm run dev

The command prints a local URL (default http://localhost:3004) and opens it. That tab is the presenter view. Press **P** (or the Present control in the capsule at the bottom) to open the audience tab; the two stay in sync. The presenter view shows the current slide, the next slide, the speaker notes (editable, saved in the browser) and an elapsed timer.

Keys: **Right / Space** next build or slide · **Left / Backspace** back · **P** present (audience tab) · **F** or the capsule button: fullscreen. Screen-share the **audience tab** (Google Meet: Share screen, A tab; Zoom: drag the audience tab into its own window and share that window).

Builds per slide (key presses after the slide appears): 1 cover 0 · 2 problem 2 · 3 solution 4 · 4 product 1 (the officer case findings at readable size) · 5 AI 3 · 6 workflow 5 · 7 principles 2 · 8 architecture 3 · 9 quality 2 · 10 next 0 · 11 closing 1. Total 34 hold points; the notes mark each with "[Next]".

Reduced motion: if the presenting machine has "reduce motion" on, the builds appear without movement.

Checks: `npx hyperframes@0.8.50 check` (lint, runtime, layout, motion, contrast; 0 errors). Snapshots of every hold point: `node snapshots.mjs http://localhost:3004/ snapshots/1280x720 1280 720 all` while the present server runs (also captured at 1440 x 900 and 1920 x 1080 in `snapshots/`).

PDF handout: the HyperFrames CLI (0.8.50) has no deck-to-PDF export and `render` would produce a truncated MP4, so there is no PDF from this version; use the PowerPoint handout PDF (same copy).

## B. PowerPoint (`pptx/`)

Files:

- `PermitFlow-pitch.pptx`: the deck to present, brand fonts referenced (Public Sans, Instrument Serif, IBM Plex Mono). On a machine without those fonts PowerPoint substitutes; the layouts were sized for that case. To get the brand fonts on a Mac or PC, install the TTFs in `pptx/fonts/` (double-click each, Font Book or the Windows font installer), then reopen the deck.
- `PermitFlow-pitch-safe-fonts.pptx`: identical deck with Arial, Cambria and Courier New written into the file, for a foreign machine where installing fonts is not an option.
- `PermitFlow-pitch-handout.pdf` and `slides/slide-01.png` to `slide-11.png`: handout state (every build in its final state), rendered from the safe-font deck.
- `fonts/`: the brand fonts as installable TTF files (SIL Open Font License 1.1; static instances of the product's own files).
- The generator (`build.cjs`, `animate.py`) and the image assets stay in the workshop folder; `content.json` here is the copy it was built from.

Present: open `PermitFlow-pitch.pptx`, Slide Show, From Beginning. Presenter View shows the notes. Each slide has one Fade transition; the Click builds: slides 2, 3, 4, 6, 7 and 9 each take one click to enter and one more click to reveal everything on the slide (the builds play as a short timed sequence). Slides 1, 5, 8, 10 and 11 have no builds.

| Slide | Clicks | What each click does |
|-------|--------|----------------------|
| 2 The problem | 2 | the loop of stages; the six frictions |
| 3 The solution | 4 | one persona band per click |
| 4 The product | 1 | the officer case at full size over the grid |
| 6 A real workflow | 5 | Revision 1 with its two findings; feedback and request; the reopened slots; Revision 2 (badges change to Verified and Addressed in Revision 2, the sub-lines to Replaced in Revision 2); Start review, resolved, site visit |
| 7 What makes it different | 2 | principles 1 to 3; principles 4 to 6 |
| 9 Engineering quality | 2 | the checklist; the scope columns |

Slides 1, 5, 8, 10 and 11 have no builds. Speaker notes mark each click with "[Click]"; on slides without builds the cue is removed from the notes.

## Which version does what

| | HTML slideshow | PowerPoint |
|---|---|---|
| Motion fidelity | The product's own tokens: pf ease, 6 px and 16 px rises, drawn paths, in-place badge changes, a zoom that travels from the grid cell | Fade only (PowerPoint's Fade or Wipe); badge changes are cross-fades |
| Presenter view | Built in: current and next slide, editable notes, timer, audience tab in sync | PowerPoint Presenter View |
| Portability | Needs Node and a browser; the deck is a folder | One file; opens anywhere PowerPoint or Keynote runs |
| Fonts on a foreign machine | Always the brand fonts (bundled) | Substituted unless the TTFs in `pptx/fonts/` are installed; a safe-font copy is provided |
| Editing afterwards | Edit `html/index.html` (copy and layout in one file) | Edit in PowerPoint directly, or change `content.json` and rebuild |
| Handout | No PDF export from the CLI | PDF and PNGs included |
| Rendering guarantee | `hyperframes check` passes, snapshots at three viewports | `validate.py` passes; renders checked with fallback fonts |
