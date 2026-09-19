# PermitFlow pitch deck: plan (rebuilt 19 Sep 2026 after the scratchpad was lost)

Audience: the Xtremax hiring panel. Goal: the reviewer concludes the candidate understood the problem, made sensible product decisions, built something real and can explain it. Not a fundraising deck. Every claim maps to a file in the repository. Not built yet.

## Format decision (open)

- Track A, recommended: an animated HTML deck, built as a HyperFrames `slideshow` (presenter mode with speaker notes, fragment reveals, `npx hyperframes present`), sharing the videos' tokens, fonts, components (badges, mark, check block) and motion. Real motion, keyboard-driven, overview grid, notes panel, reduced-motion respected.
- Track B, fallback and email attachment: `.pptx` from pptxgenjs (16:9 wide), then OOXML post-processing for a Fade transition per slide and click builds on slides 2, 3, 6, 7, 9; validated; PDF handout.
- Fonts: the product's own (Public Sans, Instrument Serif, IBM Plex Mono); in pptx, fall back to Arial and Cambria if the brand fonts are not installed.
- Copy rules: no em dashes, no emoji, no gradients, no KPI tile grids, no accent bars; numbers from `README.md` on build day (736 backend tests, 146 frontend, 7 Playwright, 96 % and 80.5 % coverage, 588 state-machine combinations, 20 threats, 4 workflows, 174 commits, 17 to 19 Sep 2026).

## Eleven slides

1. Cover (ink): PermitFlow · Modernising regulatory licensing workflows · Food Establishment Licence · Working product · Full Stack Developer Assessment · Xtremax Singapore · September 2026; officer queue screenshot at 18 % opacity.
2. The problem: the journey chain (Application, Documents, Review, Feedback, Resubmission, Review again) looping on itself; six friction lines from `docs/discovery/PROBLEM.md`. No technology words.
3. The solution: one sentence; four persona bands (Operator: Apply, Upload, AI check, Submit · Officer: Review, findings beside each document, feedback tied to a section or document, request resubmission · Operator: update only the flagged parts, resubmit · Officer: compare, resolve, continue). Every verb is a real button.
4. The product: four fresh screenshots at 1440 (operator dashboard, documents page mid-check, officer case, compare view), one-line captions, "One workflow. Two personas. Full traceability."
5. AI assists, humans decide: three tiers (per-upload verification: extract, readability, compare, flag, quote evidence, confidence · officer view: findings, closed issue codes, evidence, confidence, model and prompt version, re-run · human officer: the decision, audited); side panel "deterministic by design, not AI: feedback templates, revision compare, status changes"; footer "advisory and replaceable" (ADR-006). Operators never see evidence or confidence.
6. A real workflow: Kopi & Kaya Toast House Pte. Ltd., UEN 202355555E, 10 Jalan Besar #01-12; Revision 1 with two planted issues (expired food hygiene certificate, tenancy for unit #01-21), feedback tied to both documents, only those slots reopen, Revision 2 Verified, items Addressed then Resolved, on to the site visit. Badges as dot plus label; no emoji.
7. What makes it different: six numbered principles enforced by code (continuous workflow; immutable revisions and read-time diff; contextual feedback with "only flagged" as a 403 rule; AI-assisted with no AI actor in the state machine; same-transaction audit; role-aware, an authorization test per endpoint).
8. Designed for production: simplified architecture (React UI, FastAPI, application services, AI verification, audit trail, PostgreSQL, file storage, LLM provider); footer "Modular monolith · PostgreSQL · async AI verification · role-based access · immutable revisions · CI/CD to Railway".
9. Engineering quality: checklist with one evidence phrase each (tests, state machine, auth, validation and error envelope, audit, CI gates including the six-stage AI gate, AI evaluation 14 golden cases and 21 fairness runs, deployment behind a human approval, health gates and request ids and AI traces); three columns Implemented (UC1 + UC2, 12-state lifecycle), Deferred (UC3, statuses present), Simplified (email, storage, background processing, rate limiting).
10. What I would do next: ten items from `README.md` "What I would do next" (object storage with virus scanning; broker and worker; SSO and MFA; httpOnly cookie, CSP nonces, edge rate limiting; OCR; email delivery; UC3; configurable forms and assignment; broader AI evaluation, calibration, multilingual injection classifier, Project Moonshot; backups, staging rehearsal, SAST, image scanning).
11. Closing (ink): PermitFlow · From submission to resolution: one traceable licensing workflow · chain of pills · "Built as a production-quality MVP within a three-day engineering constraint" · URL.

Speaker notes on every slide from `docs/reviews/FINAL_REVIEW.md` and `AI_USAGE.md` section 7.

## Motion (Track A, presenter-triggered builds, never autoplay)

Cover: mark's check draws, title rises. Problem: chain assembles pill by pill, loops back. Solution: chain re-forms into bands, operator from the left, officer from the right. Product: screenshots settle with stagger, press again to zoom one full bleed. AI: tiers stack. Workflow: timeline draws, badges transition tone in place ("Issues found" to "Verified", "Open" to "Addressed" to "Resolved"). Principles: cards flip number to text. Architecture: boxes fade top down, connectors draw. Quality: checklist ticks in, stats count up once. Closing: chain lights left to right. Tokens: `pf` ease, 150 / 220 / 320 ms, E6, E16, Flip, as in the videos. Verified at 1280 x 720, 1440 x 900, 1920 x 1080.

## Assets

Fresh screenshots at 1440 (the `docs/design/screens/as-built/` captures predate the redesign): officer queue, operator dashboard, documents page mid-check, officer case with findings and rail, compare view, application page with the feedback notice. Brand mark from `docs/design/brand/`. Architecture and sequence PNGs from `docs/architecture/`.

## Open decisions

Track A then B or one only; deck committed to `docs/pitch/` or kept outside; closing URL production (after v0.3.0).
