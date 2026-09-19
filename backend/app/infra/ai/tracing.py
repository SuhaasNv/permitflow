"""LangSmith tracing for the OpenAI provider (US-055).

Off unless `LANGSMITH_API_KEY` is set. When on, every `verify()` becomes a trace: a parent run named
`verify_document` carrying our metadata (verification run id, application id, document type, prompt
version) and a child LLM run from the wrapped OpenAI client (model, tokens, latency, the raw answer).

Inputs (the extracted document text and the form section) are hidden by default: they are an applicant's
documents, and LangSmith is a hosted service (the organisation's region, US, EU or APAC in Sydney, is fixed
at sign-up; `LANGSMITH_ENDPOINT` must match it). `LANGSMITH_HIDE_INPUTS=false` reveals them, meant for the
development environment only. Outputs stay visible: status, codes, confidence, summary and the evidence
quotes, which are excerpts of at most 300 characters (`docs/06-security/THREAT_MODEL.md`, T21).

Tracing never changes a verification result and never raises into the provider: a LangSmith outage is
logged by the SDK and the check completes as if tracing were off."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any, TypeVar

C = TypeVar("C")


class Span:
    """What the provider gets back from `Tracer.run`: `end(outputs)` records the parsed result."""

    def __init__(self, run_tree: Any = None) -> None:
        self._run_tree = run_tree

    def end(self, outputs: dict[str, Any]) -> None:
        if self._run_tree is not None:
            self._run_tree.end(outputs=outputs)


class Tracer:
    """One configured LangSmith client; `enabled` is False when there is no key."""

    def __init__(
        self,
        *,
        api_key: str,
        project: str,
        hide_inputs: bool,
        endpoint: str = "https://api.smith.langchain.com",
    ) -> None:
        self.enabled = bool(api_key)
        self.project = project
        self.hide_inputs = hide_inputs
        self._client: Any = None
        if self.enabled:
            from langsmith import Client

            self._client = Client(api_url=endpoint, api_key=api_key, hide_inputs=hide_inputs)

    @contextmanager
    def run(self, name: str, *, metadata: dict[str, Any], inputs: dict[str, Any]) -> Iterator[Span]:
        """Trace everything inside as one run; a no-op span when tracing is off."""
        if not self.enabled:
            yield Span()
            return
        from langsmith.run_helpers import trace, tracing_context

        with (
            tracing_context(enabled=True, client=self._client, project_name=self.project),
            trace(name, run_type="chain", metadata=metadata, inputs=inputs) as run_tree,
        ):
            yield Span(run_tree)

    def wrap(self, client: C) -> C:
        """Wrap an OpenAI client so its calls appear as LLM runs (tokens, cost, latency, raw answer)."""
        if not self.enabled:
            return client
        from langsmith.wrappers import wrap_openai

        return wrap_openai(client, tracing_extra={"client": self._client})
