# Debrief material

What is presented at the debrief, in its final form (story US-059). Made after the code was frozen at v0.3.0 (19 September 2026); nothing here changes the product.

| File | What it is |
|------|------------|
| `pitch-deck/PermitFlow-pitch.pptx`, `PermitFlow-pitch-handout.pdf` | Thirteen slides for the debrief audience: the problem, the product (operator and officer), the AI check, a real workflow, principles, architecture, the observability dashboard, quality, next steps. The shared copy carries no presenter notes; the speaker keeps a presenter copy locally. |
| `technical-deck/PermitFlow-technical.pptx`, `PermitFlow-technical-handout.pdf` | Twenty-two slides on how it is built: the brief decoded, scope, assumptions, how the work was run (the board), architecture, four ADRs with the workflow table itself, branching, deployment, CI, observability (the Grafana dashboard), readiness evidence, AI usage (building the product; where the AI was wrong; the checked-in rules; the debrief material), next steps. Counts refreshed from the repository on 20 Sep after a cold review. No presenter notes in the shared copy. |
| `video/permitflow-launch.mp4` | Launch video, 70.7 s, 1920 x 1080, 60 fps, narrated and captioned. `permitflow-launch-poster.jpg` is its poster frame (also at the top of the README). |
| `video/permitflow-walkthrough.mp4` | Narrated walkthrough of both roles, 4 min 36 s, recorded on the development environment. |
| `video/permitflow-technical.mp4` | Technical video, 4 min: roles and the 403s, the status table, the test counts, the six-stage AI gate, the fairness sweep, scope; then how it was built (Claude Code under the checked-in `CLAUDE.md`, prompts dictated with Wispr Flow, diffs read in Cursor, the Notion board, read-only review agents, where the AI was wrong, the video skills from GitHub, and the film's own build file). Poster frame baked in. |

Videos are stored with Git LFS (`git lfs pull` after cloning if they arrive as pointer files). The diagrams in the technical deck are in `../03-architecture/diagrams/views/`. How this material was made: `AI_USAGE.md`, section 1 (second-session row) and section 4 ("Debrief material").
