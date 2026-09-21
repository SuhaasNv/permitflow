# Prototype v0.4.0 source

`build.py` generates the nineteen artboards of the v0.4.0 prototype (a Design canvas on claude.ai, linked from `docs/04-design/README.md`) from the design tokens in `DESIGN_SYSTEM.md` and the shipped app shell. Every screen comes from the same helpers (badge, tag, button, chip, panel, table, timeline, dialog, shell), so a change made once applies everywhere.

```bash
python3 docs/04-design/prototype-src/v0-4-0/build.py /tmp/proto
# writes /tmp/proto/project/*.dc.html and canvas.json; publish the folder to the canvas
```

To check a board without the canvas runtime, render the file with Playwright: `cd frontend && npx playwright screenshot --full-page --viewport-size=1300,900 file:///tmp/proto/project/Main.dc.html /tmp/main.png`.

The artboards, in canvas order: S-30 checklist at 1024 and at 820 (offline state), S-31 officer case with the clarification rail, S-18 respond at 390 (one with the send sheet) and at 1280 with the send dialog, S-19 operator history, S-40 admin overview, S-42 admin activity, S-41 admin users with the change-role dialog, S-43 admin read-only case; then the site-visit appointment row (S-32 to S-34) and the What's new row (S-44 as an officer at 1280, an operator on a phone at 390, an administrator at 1280; the notes come from the repository's `RELEASE_NOTES.md`, the file the product itself reads, so the boards and the page can never disagree). The demo data is one chronology (comments at the top of the clarification section in `build.py`). Critique pass 3 (`UI_DESIGN.md`) was applied here on 20 Sep 2026.
