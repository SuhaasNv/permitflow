# PermitFlow technical deck: how to present it

Fifteen slides, PowerPoint only, same design language as the pitch deck (tokens, type, badges, keys, ink closing). `content.json` is the source of truth; `build/build.cjs` renders it with the pitch deck's helpers, `build/animate.py` adds the Fade transition and one click build per slide that has one.

## Files

- `PermitFlow-technical.pptx`: the deck to present, brand fonts referenced (Public Sans, Instrument Serif, IBM Plex Mono; TTFs in `../pitch-deck/fonts/`).
- `PermitFlow-technical-safe-fonts.pptx`: same deck with Arial, Cambria and Courier New written in, for a machine where fonts cannot be installed.
- `PermitFlow-technical-handout.pdf` and `slides/slide-01.png` to `slide-15.png`: final state of every slide, rendered from the safe-font deck.
- The generator and the animation script stay in the workshop folder (`notes/pitch/technical/deck/build/`, git-ignored). The diagrams are in the repository at `docs/architecture/diagrams/views/` (solution architecture, deployment, CI/CD); they were generated with ChatGPT from `DIAGRAM_PROMPTS.md` in this folder and rated against the code before use.

## Order and clicks

Follows the brief's evaluation areas: scope judgement (2 to 4), code quality (5 to 9), production readiness (10 to 12), AI usage (13), documentation throughout, next steps (14).

| Slide | Clicks | The click reveals |
|-------|--------|-------------------|
| 1 Cover | 0 | |
| 2 The brief, decoded | 1 | the evaluation areas and where they are in the deck |
| 3 Scope | 1 | the DEFERRED column |
| 4 Assumptions | 0 | |
| 5 Architecture (diagram 01) | 1 | callouts 2 to 4 |
| 6 ADR-003 state machine | 1 | evidence and trade-off |
| 7 ADR-005 authorization and role views | 1 | evidence and trade-off |
| 8 ADR-006 AI advisory | 1 | evidence and trade-off |
| 9 ADR-007 and 008 revisions and audit | 1 | evidence and trade-off |
| 10 Deployment (diagram 04) | 1 | callouts 2 to 4 |
| 11 CI/CD (diagram 05) | 1 | callouts 2 to 4 |
| 12 Production readiness | 1 | the four review documents |
| 13 AI usage | 1 | the debrief-material column |
| 14 What I would do next | 0 | |
| 15 Closing | 0 | |

Speaker notes on every slide; "[Click]" marks the build. About 12 minutes at a steady pace, 20 with questions.

## Why these four ADRs

003, 005, 006, 007 with 008: each is a line of the brief that can be checked (the status table, "operators never see the approval stage", "AI results visible" with the officer deciding, "never lost between rounds" and "complete audit trail"). 001, 002, 004 and 009 are the shape and are covered on the architecture slide; 011 is the deployment slide; 004's next step (a worker) is on slide 14.

## Rebuild (workshop folder)

    cd notes/pitch/technical/deck/build
    export NODE_PATH=<folder with pptxgenjs installed>/node_modules
    FONTS=brand node build.cjs && python3 animate.py ../PermitFlow-technical.pptx ../PermitFlow-technical.pptx
    FONTS=safe OUT=../PermitFlow-technical-safe-fonts.pptx node build.cjs && python3 animate.py ../PermitFlow-technical-safe-fonts.pptx ../PermitFlow-technical-safe-fonts.pptx
    FONTS=safe HANDOUT=1 OUT=/tmp/handout.pptx node build.cjs   # then soffice --convert-to pdf, pdftoppm -r 96 -png

## Facts checked against the repository (19 Sep 2026)

748 backend tests (96 % statements), 152 frontend tests (80.6 % statements), 8 Playwright specs (journey, 6 scenarios, axe over 23 states), 18 transition rows in `domain/workflow.py`, 588 combinations in `test_workflow.py`, prompt version 2026-09-19.3, confidence threshold 0.6, 14 golden cases, 2 injection cases, 21 fairness runs, 23 threat headings (T1 to T22 plus T1a), 20 readiness rows, 12 UAT scripts, 240 requests and 20 sign-ins per minute, 20 drafts, 60 and 1 000 checks per day.
