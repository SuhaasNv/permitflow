# ADR-006: AI is advisory, structured, validated and replaceable

## Context
AI document verification is an explicit feature. It must be useful to operators (early warning) and officers (triage), but a regulator cannot delegate outcomes to a probabilistic component, and the assessment warns against uncritical reliance on AI.

## Constraints
- Uploaded documents are untrusted input (prompt injection, junk, wrong file).
- The provider may be slow, down, or unconfigured; the product must still work.
- Output must be renderable and testable.

## Options Considered

### Option A: Advisory, structured output via JSON schema, Pydantic validation, deterministic post-rules, provider interface
The model is constrained with a JSON schema (structured outputs) whose shape is the result. The response is parsed into a strict Pydantic model (`extra="forbid"`). Rules then apply: empty text → `unreadable` without calling the model; confidence < `AI_CONFIDENCE_THRESHOLD` (default 0.6, configurable; the model's confidence is self-reported and uncalibrated) downgrades `verified` to `needs_review`; the injection heuristic also forces `needs_review`. The status vocabulary and `IssueCode` enum are defined in `DOMAIN_MODEL.md`. Results attach to the document and never touch status or feedback.
- Pros: deterministic shape; testable; failures are data; provider swap is one class.
- Cons: schema-valid but wrong content is still possible; mitigated by evidence quotes and confidence shown to the officer.

### Option B: Free-form model text shown to users
- Pros: trivial.
- Cons: unparseable, untestable, injection-prone, not actionable.

### Option C: AI decides acceptance or drives status
- Pros: "smart".
- Cons: unaccountable; a hallucination becomes a regulatory decision; conflicts with the officer role.

## Decision
Option A. Provider protocol `VerificationProvider.verify(request) -> ProviderResult`; implementations `OpenAIProvider` (Chat Completions structured outputs via the official `openai` SDK, direct OpenAI API key, model from `OPENAI_MODEL`, default `gpt-4o-mini` for cost) and `MockProvider` (deterministic heuristics used in tests and when no key is set). Selection by `AI_PROVIDER` environment variable.

Structured-output detail: OpenAI strict JSON schema mode rejects `minimum`/`maximum`/`pattern` keywords, so two models exist — a *wire* model (enums and required fields only, used to build the schema) and a *domain* model (adds bounds such as `0 ≤ confidence ≤ 1`, `extra="forbid"`) that the wire output is validated into. A wire-valid but domain-invalid result is a `failed` run with `raw_output_valid = false`.

## Rationale
This keeps the value of AI (early, specific problem detection) while keeping accountability with humans and keeping the system functional without AI. Structured output is what makes the results renderable, comparable and evaluable.

## Consequences

### Positive
- The verification pipeline is a pure function of (document text, document type, form data) → validated result, which is exactly what an evaluation set needs.
- No code path from AI output to authoritative state; reviewable by grep.

### Negative / Tradeoffs
- Only text-extractable documents (PDF text layer, TXT) are verified; images are marked `unreadable` with a reason. OCR is a documented gap.
- Prompt injection can still degrade the *advice*; it cannot change state. Detection heuristics flag suspicious instruction-like text for the officer.

## Validation
- Unit tests: malformed JSON, missing fields, extra fields, out-of-range confidence, injected instructions in text → handled as specified.
- Evaluation set in `backend/evals/` with six cases and a runner script; results recorded in `docs/ai/AI_EVALUATION.md`.
- Integration test: with provider raising, upload and submission succeed.
