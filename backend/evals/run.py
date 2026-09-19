"""Run the golden cases through the real verification pipeline (extraction, injection heuristic, provider,
post-processing rules) without a database, and report expected versus actual (US-004, AI-008).

    uv run python -m evals.run --provider mock                # hermetic, what CI runs
    uv run python -m evals.run --provider openai --json out.json   # needs OPENAI_API_KEY
    uv run python -m evals.run --provider mock --fail-under 1.0    # exit 1 below the pass rate
    uv run python -m evals.run --provider openai --langsmith       # also record as a LangSmith experiment

Cases marked `mock_gap` are expected to fail on the mock (its heuristics are deliberately simple);
they still run and are reported, but do not count against the mock's pass rate.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from app.core.settings import get_settings
from app.domain.verification_rules import (
    DOCUMENT_TYPE_DESCRIPTIONS,
    SECTION_FOR_DOCUMENT,
    VerificationRequest,
    apply_rules,
    find_injection_phrases,
)
from app.infra.ai.base import VerificationProvider
from app.infra.ai.mock import MockProvider
from app.infra.ai.openai_provider import PROMPT_VERSION
from app.infra.extraction import extract_text

HERE = Path(__file__).resolve().parent


@dataclass
class Outcome:
    id: str
    group: str
    document_type: str
    expected: str
    actual: str
    codes: list[str]
    passed: bool
    counted: bool
    ms: int
    note: str


def _provider(name: str) -> VerificationProvider:
    if name == "mock":
        return MockProvider()
    settings = get_settings()
    if not settings.openai_api_key:
        raise SystemExit("OPENAI_API_KEY is not set; use --provider mock")
    from app.infra.ai.openai_provider import OpenAIProvider

    return OpenAIProvider(
        api_key=settings.openai_api_key, model=settings.openai_model, timeout=settings.ai_timeout_seconds
    )


def _content_type(path: Path) -> str:
    return "application/pdf" if path.suffix.lower() == ".pdf" else "text/plain"


def run_case(case: dict[str, Any], form: dict[str, Any], provider: VerificationProvider) -> Outcome:
    settings = get_settings()
    path = (HERE / case["file"]).resolve()
    data = path.read_bytes()
    started = time.perf_counter()
    extracted = extract_text(_content_type(path), data, max_chars=settings.ai_max_text_chars)
    truncated = len(extracted.text) >= settings.ai_max_text_chars
    codes: list[str] = []
    if extracted.reason:
        actual = "unreadable"
        note = f"extraction: {extracted.reason}"
    else:
        injection = find_injection_phrases(extracted.text)
        doc_type = case["document_type"]
        request = VerificationRequest(
            document_type=doc_type,
            document_type_description=DOCUMENT_TYPE_DESCRIPTIONS[doc_type],
            form_section=dict(form.get(SECTION_FOR_DOCUMENT[doc_type]) or {}),
            text=extracted.text,
        )
        result = provider.verify(request)
        outcome = apply_rules(
            result, confidence_threshold=settings.ai_confidence_threshold, injection_phrases=injection
        )
        actual = outcome.status.value
        codes = sorted({str(i["code"]) for i in outcome.issues})
        note = result.summary[:90]
    ms = int((time.perf_counter() - started) * 1000)

    expect = case["expect"]
    allowed = expect.get("status_in") or [expect["status"]]
    ok = actual in allowed
    for code in expect.get("codes", []):
        ok = ok and code in codes
    if expect.get("truncated"):
        ok = ok and truncated
        note = f"truncated to {settings.ai_max_text_chars} chars; " + note
    counted = not (provider.name == "mock" and case.get("mock_gap"))
    expected = "|".join(allowed) + (f" +{','.join(expect['codes'])}" if expect.get("codes") else "")
    return Outcome(
        case["id"], case["group"], case["document_type"], expected, actual, codes, ok, counted, ms, note
    )


DATASET = "permitflow-golden-set"


def _run_as_experiment(spec: dict[str, Any], provider: VerificationProvider) -> list[Outcome]:
    """The same cases, run once each through LangSmith's `evaluate`, so the result is an experiment on the
    golden dataset (pass rate history per prompt version) as well as the console table (US-055)."""
    from langsmith import Client, evaluate

    settings = get_settings()
    if not settings.langsmith_api_key:
        raise SystemExit("LANGSMITH_API_KEY is not set; drop --langsmith")
    client = Client(
        api_url=settings.langsmith_endpoint,
        api_key=settings.langsmith_api_key,
        hide_inputs=settings.langsmith_hide_inputs,
    )
    cases = {c["id"]: c for c in spec["cases"]}
    if not client.has_dataset(dataset_name=DATASET):
        client.create_dataset(DATASET, description="PermitFlow golden and adversarial cases (cases.json)")
        client.create_examples(
            dataset_name=DATASET,
            examples=[
                {
                    "inputs": {"id": c["id"], "group": c["group"], "document_type": c["document_type"]},
                    "outputs": {"expect": c["expect"]},
                }
                for c in spec["cases"]
            ],
        )
    outcomes: dict[str, Outcome] = {}

    def target(inputs: dict[str, Any]) -> dict[str, Any]:
        outcome = run_case(cases[inputs["id"]], spec["form"], provider)
        outcomes[outcome.id] = outcome
        return {"status": outcome.actual, "codes": outcome.codes, "ms": outcome.ms}

    def passed(run: Any, example: Any) -> dict[str, Any]:
        outcome = outcomes[example.inputs["id"]]
        return {"key": "passed", "score": int(outcome.passed), "comment": outcome.note}

    evaluate(
        target,
        data=DATASET,
        evaluators=[passed],
        experiment_prefix=f"{provider.name}-{PROMPT_VERSION}",
        metadata={"provider": provider.name, "model": provider.model, "prompt_version": PROMPT_VERSION},
        client=client,
        max_concurrency=1,
    )
    return [outcomes[c["id"]] for c in spec["cases"]]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--provider", choices=["mock", "openai"], default="mock")
    parser.add_argument("--json", type=Path, help="write the outcomes as JSON")
    parser.add_argument("--group", help="run only the cases in this group (clean, issues, edge, adversarial)")
    parser.add_argument(
        "--fail-under", type=float, default=None, help="exit 1 when the pass rate is below this"
    )
    parser.add_argument(
        "--langsmith",
        action="store_true",
        help="run the cases as a LangSmith experiment on the golden dataset (needs LANGSMITH_API_KEY)",
    )
    args = parser.parse_args(argv)

    spec = json.loads((HERE / "cases.json").read_text())
    if args.group:
        spec["cases"] = [c for c in spec["cases"] if c["group"] == args.group]
        if not spec["cases"]:
            raise SystemExit(f"no cases in group {args.group!r}")
    provider = _provider(args.provider)
    if args.langsmith:
        outcomes = _run_as_experiment(spec, provider)
    else:
        outcomes = [run_case(c, spec["form"], provider) for c in spec["cases"]]

    width = max(len(o.id) for o in outcomes)
    print(f"provider={provider.name} model={provider.model or '-'} prompt={PROMPT_VERSION}")
    print(f"{'case':<{width}}  {'expected':<34} {'actual':<14} {'result':<9} ms")
    for o in outcomes:
        mark = "pass" if o.passed else ("gap" if not o.counted else "FAIL")
        print(f"{o.id:<{width}}  {o.expected:<34} {o.actual:<14} {mark:<9} {o.ms}")
        if o.codes:
            print(f"{'':<{width}}  codes: {', '.join(o.codes)}")
    counted = [o for o in outcomes if o.counted]
    passed = sum(1 for o in counted if o.passed)
    rate = passed / len(counted) if counted else 0.0
    gaps = sum(1 for o in outcomes if not o.counted)
    print(
        f"\n{passed}/{len(counted)} counted cases passed ({rate:.0%}); "
        f"{gaps} known mock gaps reported, not counted"
    )

    if args.json:
        args.json.write_text(
            json.dumps(
                {
                    "provider": provider.name,
                    "model": provider.model,
                    "prompt_version": PROMPT_VERSION,
                    "pass_rate": rate,
                    "passed": passed,
                    "counted": len(counted),
                    "outcomes": [asdict(o) for o in outcomes],
                },
                indent=2,
            )
        )
    if args.fail_under is not None and rate < args.fail_under:
        print(f"pass rate {rate:.0%} is below {args.fail_under:.0%}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
