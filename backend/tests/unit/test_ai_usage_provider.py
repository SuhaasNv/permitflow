"""US-100: the providers report the tokens they billed, so the usage record can price the check."""

import json
import uuid
from types import SimpleNamespace
from typing import Any

import pytest

from app.domain.verification_rules import DOCUMENT_TYPE_DESCRIPTIONS, VerificationRequest
from app.infra.ai.base import ProviderError
from app.infra.ai.mock import MockProvider
from app.infra.ai.openai_provider import OpenAIProvider
from app.services.ai_usage import trace_ids


def _request() -> VerificationRequest:
    return VerificationRequest(
        document_type="floor_plan",
        document_type_description=DOCUMENT_TYPE_DESCRIPTIONS["floor_plan"],
        form_section={},
        text="Floor plan: kitchen and dining area marked.",
    )


def _install(monkeypatch: pytest.MonkeyPatch, completion: Any) -> None:
    import openai

    client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=lambda **_kw: completion))
    )
    monkeypatch.setattr(openai, "OpenAI", lambda **_kw: client)


def _completion(content: str | None, usage: Any) -> Any:
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))], usage=usage)


def test_the_mock_bills_nothing() -> None:
    p = MockProvider()
    p.verify(_request())
    assert (p.input_tokens, p.output_tokens) == (0, 0)


def test_openai_reports_prompt_and_completion_tokens(monkeypatch: pytest.MonkeyPatch) -> None:
    answer = {
        "status": "verified",
        "confidence": 0.9,
        "summary": "ok",
        "issues": [],
        "missing_information": [],
    }
    usage = SimpleNamespace(prompt_tokens=1200, completion_tokens=80, prompt_tokens_details=None)
    _install(monkeypatch, _completion(json.dumps(answer), usage))
    p = OpenAIProvider(api_key="sk-test", model="gpt-4.1-mini", timeout=5)
    assert (p.input_tokens, p.output_tokens) == (0, 0)  # nothing billed before a call
    p.verify(_request())
    assert (p.input_tokens, p.output_tokens) == (1200, 80)


def test_a_malformed_answer_was_still_billed(monkeypatch: pytest.MonkeyPatch) -> None:
    usage = SimpleNamespace(prompt_tokens=900, completion_tokens=12, prompt_tokens_details=None)
    _install(monkeypatch, _completion('{"status": "rejected"}', usage))
    p = OpenAIProvider(api_key="sk-test", model="gpt-4.1-mini", timeout=5)
    with pytest.raises(ProviderError):
        p.verify(_request())
    assert (p.input_tokens, p.output_tokens) == (900, 12)


def test_a_response_without_usage_counts_as_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    answer = {
        "status": "verified",
        "confidence": 0.9,
        "summary": "ok",
        "issues": [],
        "missing_information": [],
    }
    _install(monkeypatch, _completion(json.dumps(answer), None))
    p = OpenAIProvider(api_key="sk-test", model="gpt-4.1-mini", timeout=5)
    p.verify(_request())
    assert (p.input_tokens, p.output_tokens) == (0, 0)


def test_trace_ids_without_a_user_carry_only_the_case_hash() -> None:
    ids = trace_ids(None, uuid.uuid4())
    assert set(ids) == {"application_hash"}
    both = trace_ids(uuid.uuid4(), uuid.uuid4())
    assert set(both) == {"application_hash", "user_pseudonym"}
