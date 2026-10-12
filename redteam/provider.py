"""promptfoo Python provider: the real document-check pipeline behind one function (US-106).

promptfoo hands the attack text as `prompt`; this runs it through `evals.run.run_case` (extract_text,
prepare_text, provider, apply_rules) and returns the verdict as JSON for the grader.

The provider is the MOCK unless REDTEAM_PROVIDER=openai is set. A live run needs the owner's yes and stays
within the 200-call cap in docs/07-ai/RED_TEAM.md.
"""

import json
import os
import sys
from pathlib import Path
from typing import Any

BACKEND = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND))

from evals.redteam.run import run_document  # noqa: E402
from evals.run import HERE, _provider  # noqa: E402


def call_api(prompt: str, options: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    doc_type = (options.get("config") or {}).get("documentType", "tenancy_agreement")
    spec = json.loads((HERE / "cases.json").read_text())
    outcome = run_document(
        spec,
        doc_type,
        prompt.encode(),
        ".txt",
        "promptfoo",
        _provider(os.environ.get("REDTEAM_PROVIDER", "mock")),
    )
    return {
        "output": json.dumps(
            {"status": outcome.actual, "issue_codes": outcome.codes, "summary": outcome.note}
        )
    }
