from app.core.settings import get_settings
from app.infra.ai.base import VerificationProvider
from app.infra.ai.mock import MockProvider


def get_provider() -> VerificationProvider | None:
    """`None` means "not configured": the run is stored as `unavailable` (AI-006)."""
    settings = get_settings()
    if settings.ai_provider == "mock":
        provider: VerificationProvider = MockProvider()
        return provider
    if settings.ai_provider == "openai":
        if not settings.openai_api_key:
            return None
        from app.infra.ai.openai_provider import OpenAIProvider

        return OpenAIProvider(
            api_key=settings.openai_api_key, model=settings.openai_model, timeout=settings.ai_timeout_seconds
        )
    return None
