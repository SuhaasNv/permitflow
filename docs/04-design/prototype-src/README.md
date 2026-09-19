# Prototype generator

The clickable prototype (Design canvas linked from `../README.md`) is generated, not hand-edited, so the 23 artboards share one CSS and one component library.

- `css.py`: the design tokens and every component class (single source for `DESIGN_SYSTEM.md` values).
- `lib.py`: icons, logo mark, status label table, shell (masthead, top bar, side nav), badges, document card, verification block, feedback item, timeline, stepper.
- `screens_operator.py`, `screens_officer.py`, `screens_misc.py`: one function per artboard, realistic fictional Singapore data.
- `build.py`: writes `project/<Name>.dc.html` for the canvas plus `static/<Name>.html` for browser review, and `project/canvas.json` (frame positions, row titles). Strips em dashes from all copy.
- `shoot.sh`: full-page screenshots of every static screen with Playwright (`npx playwright@1.58.0 screenshot`), used for the design-critique passes and for `../screens/`.

Run: `python3 build.py && (cd static && python3 -m http.server 8765 &) && ./shoot.sh`. Publish `project/` to the canvas with the Artifact tool (root = this folder).
