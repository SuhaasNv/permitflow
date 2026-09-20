# 07 AI

The AI inside the product: the document verifier that reads an uploaded file and says whether it matches the application form. It advises; a person decides. This folder is the design, the measurement and the assurance story for that one component. How AI tools were used to build the product is a different subject and lives at the repository root in `AI_USAGE.md`.

| Document | What it holds |
|----------|---------------|
| `AI_VERIFICATION_DESIGN.md` | The pipeline from upload to result: text extraction and its caps, the injection heuristic, the provider interface (OpenAI behind it, a deterministic mock without a key), the prompt contract and its version, the strict output schema, the deterministic rules after the model, failure handling |
| `AI_EVALUATION.md` | The golden set (14 cases), the adversarial cases, how to run the harness, results on the mock and on the live model, what the harness caught |
| `AI_ASSURANCE.md` | One page for "how do you know the answer is legitimate": the four layers, the six-stage AI gate in CI, the nightly live evaluation, the fairness check (21 name-swapped runs), tracing, the tools chosen and not chosen |

Start with `AI_ASSURANCE.md` (five minutes), then the design if you want to read the code alongside it. The code: `backend/app/services/verification.py`, `backend/app/infra/ai/`, `backend/app/domain/verification_rules.py`; the harness: `backend/evals/`; the gate: `.github/workflows/ai-gate.yml` and `ai-eval.yml`.
