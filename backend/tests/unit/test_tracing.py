"""LangSmith tracing is off without a key, never touches the result, and when on records our ids and the
prompt version on the parent run with the document text kept out of the inputs (US-055)."""

import json
from contextlib import contextmanager
from types import SimpleNamespace
from typing import Any

import pytest

from app.domain.verification_rules import DOCUMENT_TYPE_DESCRIPTIONS, VerificationRequest
from app.infra.ai.openai_provider import PROMPT_VERSION, OpenAIProvider
from app.infra.ai.tracing import Span, Tracer


def test_tracer_without_a_key_is_a_no_op() -> None:
    tracer = Tracer(api_key="", project="permitflow", hide_inputs=True)
    assert tracer.enabled is False
    client = object()
    assert tracer.wrap(client) is client
    with tracer.run("verify_document", metadata={}, inputs={}) as span:
        assert isinstance(span, Span)
        span.end(outputs={"status": "verified"})  # nothing to record, nothing raised


def test_tracer_with_a_key_hides_inputs_and_records_the_run(monkeypatch: pytest.MonkeyPatch) -> None:
    import langsmith
    import langsmith.run_helpers
    import langsmith.wrappers

    created: dict[str, Any] = {}
    seen: dict[str, Any] = {}

    class FakeClient:
        def __init__(self, **kwargs: Any) -> None:
            created.update(kwargs)

    class FakeRunTree:
        def end(self, *, outputs: dict[str, Any]) -> None:
            seen["outputs"] = outputs

    @contextmanager
    def fake_trace(name: str, run_type: str, **kwargs: Any) -> Any:
        seen["name"], seen["kwargs"] = name, kwargs
        yield FakeRunTree()

    @contextmanager
    def fake_tracing_context(**kwargs: Any) -> Any:
        seen["context"] = kwargs
        yield

    monkeypatch.setattr(langsmith, "Client", FakeClient)
    monkeypatch.setattr(langsmith.run_helpers, "trace", fake_trace)
    monkeypatch.setattr(langsmith.run_helpers, "tracing_context", fake_tracing_context)
    monkeypatch.setattr(langsmith.wrappers, "wrap_openai", lambda client, **_kw: ("wrapped", client))

    tracer = Tracer(
        api_key="ls-test",
        project="permitflow-dev",
        hide_inputs=True,
        endpoint="https://apac.api.smith.langchain.com",
    )
    assert tracer.enabled
    assert created == {
        "api_url": "https://apac.api.smith.langchain.com",
        "api_key": "ls-test",
        "hide_inputs": True,
    }
    wrapped: Any = tracer.wrap("client")
    assert wrapped == ("wrapped", "client")
    with tracer.run("verify_document", metadata={"prompt_version": "x"}, inputs={"text_chars": 3}) as span:
        span.end(outputs={"status": "verified"})
    assert seen["name"] == "verify_document"
    assert seen["kwargs"]["metadata"] == {"prompt_version": "x"}
    assert seen["kwargs"]["inputs"] == {"text_chars": 3}
    assert seen["context"]["project_name"] == "permitflow-dev" and seen["context"]["enabled"] is True
    assert seen["outputs"] == {"status": "verified"}


class RecordingTracer(Tracer):
    """A tracer that records what the provider hands it, without LangSmith."""

    def __init__(self) -> None:
        super().__init__(api_key="", project="", hide_inputs=True)
        self.calls: list[dict[str, Any]] = []
        self.wrapped = 0

    @contextmanager
    def run(self, name: str, *, metadata: dict[str, Any], inputs: dict[str, Any]) -> Any:
        call: dict[str, Any] = {"name": name, "metadata": metadata, "inputs": inputs}
        self.calls.append(call)

        class _Span(Span):
            def end(self, outputs: dict[str, Any]) -> None:
                call["outputs"] = outputs

        yield _Span()

    def wrap(self, client: Any) -> Any:
        self.wrapped += 1
        return client


def test_provider_traces_one_run_per_check_with_our_ids(monkeypatch: pytest.MonkeyPatch) -> None:
    import openai

    answer = {
        "status": "verified",
        "confidence": 0.9,
        "summary": "Fine.",
        "issues": [],
        "missing_information": [],
    }
    message = SimpleNamespace(content=json.dumps(answer))
    completion = SimpleNamespace(choices=[SimpleNamespace(message=message)])
    completions = SimpleNamespace(create=lambda **_kw: completion)
    client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    monkeypatch.setattr(openai, "OpenAI", lambda **_kw: client)

    tracer = RecordingTracer()
    provider = OpenAIProvider(api_key="sk-test", model="gpt-4.1-mini", timeout=5, tracer=tracer)
    request = VerificationRequest(
        document_type="floor_plan",
        document_type_description=DOCUMENT_TYPE_DESCRIPTIONS["floor_plan"],
        form_section={"address_line_1": "10 Jalan Besar #01-12"},
        text="Floor plan of 10 Jalan Besar #01-12.",
        extra={"verification_run_id": "run-1", "application_id": "app-1"},
    )
    result = provider.verify(request)

    assert result.status == "verified"
    assert tracer.wrapped == 1
    (call,) = tracer.calls
    assert call["name"] == "verify_document"
    assert call["metadata"]["prompt_version"] == PROMPT_VERSION
    assert call["metadata"]["verification_run_id"] == "run-1"
    assert call["metadata"]["application_id"] == "app-1"
    # The document text never travels as an input; only its size does.
    assert call["inputs"] == {"document_type": "floor_plan", "text_chars": len(request.text)}
    assert "Jalan Besar" not in json.dumps(call["inputs"])
    assert call["outputs"]["status"] == "verified" and call["outputs"]["confidence"] == 0.9
