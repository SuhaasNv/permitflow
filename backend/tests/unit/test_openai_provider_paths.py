"""The OpenAI provider's live code path with a stubbed SDK client: every failure class maps to the right
provider outcome (AI-006, ADR-006), and the provider factory honours the configuration (US-053)."""

import json
from types import SimpleNamespace
from typing import Any

import pytest

from app.core import settings as settings_module
from app.domain.verification_rules import DOCUMENT_TYPE_DESCRIPTIONS, VerificationRequest
from app.infra.ai import factory
from app.infra.ai.base import ProviderError, ProviderUnavailable
from app.infra.ai.mock import MockProvider
from app.infra.ai.openai_provider import OpenAIProvider


def _request() -> VerificationRequest:
    return VerificationRequest(
        document_type="floor_plan",
        document_type_description=DOCUMENT_TYPE_DESCRIPTIONS["floor_plan"],
        form_section={"address_line_1": "10 Jalan Besar #01-12"},
        text="Floor plan of 10 Jalan Besar #01-12, kitchen and dining marked.",
    )


class _FakeCompletions:
    def __init__(self, outcome: Any) -> None:
        self.outcome = outcome
        self.kwargs: dict[str, Any] = {}

    def create(self, **kwargs: Any) -> Any:
        self.kwargs = kwargs
        if isinstance(self.outcome, BaseException):
            raise self.outcome
        return self.outcome


def _client_with(outcome: Any) -> tuple[Any, _FakeCompletions]:
    completions = _FakeCompletions(outcome)
    client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    return client, completions


def _completion(content: str | None) -> Any:
    usage = SimpleNamespace(
        prompt_tokens=1200, completion_tokens=80, prompt_tokens_details=SimpleNamespace(cached_tokens=1024)
    )
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))], usage=usage)


@pytest.fixture
def provider(monkeypatch: pytest.MonkeyPatch) -> tuple[OpenAIProvider, dict[str, Any]]:
    """An OpenAIProvider whose SDK client is replaced; the dict receives the fake completions object."""
    holder: dict[str, Any] = {}

    def install(outcome: Any) -> None:
        client, completions = _client_with(outcome)
        holder["completions"] = completions
        import openai

        monkeypatch.setattr(openai, "OpenAI", lambda **_kw: client)

    holder["install"] = install
    return OpenAIProvider(api_key="sk-test", model="gpt-4.1-mini", timeout=5), holder


def test_valid_answer_is_parsed_bounded_and_sent_with_the_strict_schema(
    provider: tuple[OpenAIProvider, dict[str, Any]],
) -> None:
    p, h = provider
    answer = {
        "status": "issues_found",
        "confidence": 0.9,
        "summary": "s" * 5000,
        "issues": [
            {"code": "field_mismatch", "severity": "high", "message": "m" * 900, "evidence": "e" * 900}
        ],
        "missing_information": ["x" * 400],
    }
    h["install"](_completion(json.dumps(answer)))
    result = p.verify(_request())
    assert result.status == "issues_found"
    assert len(result.summary) == 2000  # trimmed to the domain limit instead of failing the run (B9)
    assert len(result.issues[0].message) == 500 and len(result.issues[0].evidence or "") == 300
    assert len(result.missing_information[0]) == 200
    kwargs = h["completions"].kwargs
    assert kwargs["model"] == "gpt-4.1-mini" and kwargs["temperature"] == 0
    assert kwargs["response_format"]["json_schema"]["strict"] is True
    assert kwargs["messages"][0]["role"] == "system" and "<document>" in kwargs["messages"][1]["content"]
    # billing counters (US-077): prompt, its cached part, completion
    from app.core import metrics

    sample = metrics.OPENAI_TOKENS.labels("gpt-4.1-mini", "prompt")._value.get()
    assert sample >= 1200
    assert metrics.OPENAI_TOKENS.labels("gpt-4.1-mini", "cached")._value.get() >= 1024
    assert metrics.OPENAI_TOKENS.labels("gpt-4.1-mini", "completion")._value.get() >= 80


def test_timeout_and_connection_failures_are_unavailable_not_errors(
    provider: tuple[OpenAIProvider, dict[str, Any]],
) -> None:
    import openai

    p, h = provider
    h["install"](openai.APITimeoutError(request=SimpleNamespace()))  # type: ignore[arg-type]
    with pytest.raises(ProviderUnavailable):
        p.verify(_request())
    h["install"](openai.APIConnectionError(request=SimpleNamespace()))  # type: ignore[arg-type]
    with pytest.raises(ProviderUnavailable):
        p.verify(_request())


def test_other_api_failures_empty_and_malformed_answers_are_provider_errors(
    provider: tuple[OpenAIProvider, dict[str, Any]],
) -> None:
    p, h = provider
    h["install"](RuntimeError("rate limited"))
    with pytest.raises(ProviderError, match="rate limited"):
        p.verify(_request())
    h["install"](_completion(None))
    with pytest.raises(ProviderError, match="empty response"):
        p.verify(_request())
    h["install"](_completion('{"status": "rejected", "confidence": 2}'))
    with pytest.raises(ProviderError, match="schema validation failed"):
        p.verify(_request())


def test_factory_selects_the_configured_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    def with_env(**env: str) -> Any:
        # An empty value beats the developer's .env file, which pydantic-settings would otherwise read.
        for key in ("AI_PROVIDER", "OPENAI_API_KEY"):
            monkeypatch.setenv(key, "")
        for key, value in env.items():
            monkeypatch.setenv(key, value)
        settings_module.get_settings.cache_clear()
        try:
            return factory.get_provider()
        finally:
            settings_module.get_settings.cache_clear()

    monkeypatch.setenv("APP_ENV", "test")
    assert isinstance(with_env(AI_PROVIDER="mock"), MockProvider)
    # Configured for OpenAI but no key: runs are stored as unavailable.
    assert with_env(AI_PROVIDER="openai") is None
    live = with_env(AI_PROVIDER="openai", OPENAI_API_KEY="sk-test")
    assert isinstance(live, OpenAIProvider) and live.name == "openai"
    # The setting is a closed vocabulary: anything else is refused at startup, not silently "no AI".
    with pytest.raises(Exception, match="mock' or 'openai"):
        with_env(AI_PROVIDER="none")
