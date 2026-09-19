# AI assurance: how PermitFlow knows the verifier's answers are legitimate

One page for the question "how do you evaluate the AI, and what stops a bad answer from mattering?". Written 19 Sep 2026 (US-054, US-055, US-056). Detail lives in `AI_VERIFICATION_DESIGN.md` (the pipeline), `AI_EVALUATION.md` (the numbers), `../security/THREAT_MODEL.md` (T16, T18, T21) and `../architecture/decisions/ADR-006`.

## The one-minute version

The AI reads a supporting document and says whether it matches the application form. It never decides anything: it produces a hint with evidence, and a licensing officer decides. Four layers make that hint trustworthy, and two pipelines check them on every change.

| Layer | What it guarantees | Where |
|-------|--------------------|-------|
| 1. Deterministic guards | The model cannot invent a status, an issue code or a field (strict JSON schema on the wire, closed enums); an answer that contradicts itself is settled by the domain model; evidence must be quoted; confidence below 0.6 forces `needs_review`; text that tries to instruct the model is flagged before the model sees it | `app/infra/ai/openai_provider.py`, `app/domain/verification_rules.py` |
| 2. Golden set | 14 labelled cases (4 clean demo documents, 3 with planted mismatches, 5 edge cases, 2 injections) run through the real pipeline with an expected status and issue codes each | `backend/evals/cases.json`, `evals/run.py` |
| 3. Fairness check | The same document with the applicant's and the business's names swapped for names from Singapore's Chinese, Malay, Indian, Eurasian and Western communities must get the same status and codes: 7 name sets, 3 scenarios, 21 runs, every one must match its baseline | `evals/fairness.py` |
| 4. Traceability | Every check stores provider, model, prompt version, status, issues, confidence and latency; with LangSmith on, the same check is a trace with tokens and the raw answer, found by its verification run id | `verification_runs` table, `app/infra/ai/tracing.py` |

## Two pipelines

**AI gate** (`.github/workflows/ai-gate.yml`, a reusable workflow called by `ci.yml` on every push and pull request, so it shows as six jobs inside the CI run and not as a workflow of its own; mock provider, free, deterministic). Six stages, each a job named in the run summary:

1. Model approval: the model is the pinned `gpt-4.1-mini`, the confidence threshold is sane, the text cap has not grown, the prompt says the model does not make decisions, every enum on the wire is closed, the domain model forbids unknown fields, tests use the mock, no tracing key in CI.
2. Contracts: unit tests for the rules, the wire schema, the provider's failure paths (timeout, refusal, malformed answer), the mock, extraction, tracing and the rate limiter. (Found on 19 Sep after the first runs: this stage had reported "pass" while every test errored at setup, because the job had no database and the exit code was hidden behind a pipe. Fixed the same day: a Postgres service, `pipefail`, and a guard that fails the stage unless pytest reports passes.)
3. Golden set: 14 cases, blocking at 100 % of the 12 counted (two documented mock gaps are reported, not counted).
4. Adversarial: the two injection cases must land on `needs_review` with `possible_prompt_injection`.
5. Fairness: 21 name-swapped runs must match their baseline.
6. Verdict: one table, approved or blocked.

**AI evaluation, live** (`.github/workflows/ai-eval.yml`, nightly at 04:00 Singapore, by hand, and on any push that touches the AI module, the rules, the extraction or the cases; needs the `OPENAI_API_KEY` secret; never on pull requests). The same golden set and the same fairness check against the real model, temperature 0, blocking at 14 of 14 and 21 of 21, model and prompt version stamped in the result, results kept 90 days. With a `LANGSMITH_API_KEY` secret the run is also an experiment on the golden dataset, so the pass rate has a history per prompt version.

Why two: the gate proves the plumbing can never pass a bad answer through and runs on every change for free; the live run proves the model still answers correctly with this prompt and costs money, so it runs when the AI changes, not when a button moves.

## What the fairness check found the first time it ran (19 Sep 2026)

Two of 21 runs differed: "Lim Boon Keat" and "Emily Johnson" got issues on a clean certificate. The cause was the harness, not the model: the form still carried the baseline applicant's email (`weiling.tan@…`) and the business profile still named `TAN WEI LING` as director in upper case, so the model was right to say the form and the document disagreed. Once every appearance of the baseline particulars was swapped (title case, upper case, email), 21 of 21 matched on two consecutive live runs. The check is kept as written: a verifier that notices a form whose email belongs to someone else is doing its job, and a fairness check that hides that would be measuring the wrong thing.

## Honest limits

- The golden set is 14 cases and the fairness set is 7 names. Enough to catch a broken prompt, not enough to estimate accuracy to a percentage point. The set is meant to grow from officer overrides (each is a candidate case; with tracing on, it can be found by run id and added to the LangSmith dataset).
- Fairness here means invariance to names. It does not cover documents in Chinese, Malay or Tamil, image-only documents (reported as unreadable, never guessed), or confidence calibration (the 0.6 threshold is a policy choice, not a measured one).
- The injection defence is a phrase list plus the prompt's instruction; a multilingual classifier (Llama Prompt Guard 2) would be the production step.
- Bias in the licensing decision itself is out of the AI's reach by design: the officer decides, and every decision is audited with actor and time.

## Tools, and what was chosen instead

| Commonly asked about | PermitFlow | Why |
|---|---|---|
| promptfoo | Own harness (`evals/run.py`, `evals/fairness.py`) | Same job (cases, expected outcomes, blocking gate) through the real pipeline in ~200 lines of typed Python; no second config language, no second runtime |
| LangSmith | Yes, optional, behind a key (US-055) | Traces and experiment history; inputs hidden by default because the traces would carry applicants' documents; region fixed at sign-up (APAC is Sydney) |
| Bias scanning of prompts | Not done | The prompt has no demographic content to scan; the fairness check tests behaviour instead of wording |
| Risk score with weights | Not done | Pass or fail per stage is honest at this scale; a weighted score over 14 cases would be precision the data does not have |
| Project Moonshot, IMDA Starter Kit | Named as the next step | The Singapore assurance framing for a real deployment (`../reviews/PRODUCTION_READINESS_REVIEW.md`, gap 9) |
