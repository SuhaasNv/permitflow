# Debrief material

Everything prepared for the debrief, in its final form. All of it was made after the code was frozen at v0.3.0 (19 September 2026), from the repository as the source of truth, and none of it changes the product. The videos are stored with Git LFS (`git lfs pull` after cloning if they arrive as pointer files).

| Folder | What is in it |
|--------|---------------|
| `pitch-deck/` | Eleven slides for the hiring panel: `PermitFlow-pitch.pptx` (brand fonts, TTFs in `fonts/`), `PermitFlow-pitch-safe-fonts.pptx`, `PermitFlow-pitch-handout.pdf`, `slides/` (PNG per slide), `content.json` (the copy and speaker notes), `NOTES.md` (how to present, clicks per slide) |
| `technical-deck/` | Fifteen slides on how it is built: scope, assumptions, architecture, four ADRs, deployment, CI, readiness evidence, AI usage, next steps. Same files as above plus `DIAGRAM_PROMPTS.md` (the prompts the diagrams were generated from, with the acceptance list used to rate them) |
| `video/` | `permitflow-launch.mp4` (70.7 s, 1920 x 1080, 60 fps) with `launch.srt`, its poster and the share copy; `permitflow-walkthrough.mp4` (4 min 36 s, narrated) with `walkthrough.srt`, its poster and `walkthrough-narration.md` |

The diagrams used in the technical deck live with the architecture documents: `../architecture/diagrams/views/` (solution architecture, deployment, CI/CD), embedded in `../architecture/ARCHITECTURE.md` and `../operations/OPERATIONS.md`.

How this material was made, which tools and skills, and what was rejected: `AI_USAGE.md` section 1 (the second-session row) and section 4 ("Debrief material"). Footage was recorded on the development environment with its own demonstration data; production was never touched.
