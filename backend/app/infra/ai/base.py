from typing import Protocol

# ruff: noqa: N818 - outcome names, translated to run statuses by the service
from app.domain.verification_rules import VerificationRequest, VerificationResult


class ProviderError(Exception):
    """The provider answered but the answer was unusable (schema violation, refusal): stored as `failed`."""


class ProviderUnavailable(Exception):
    """No provider configured, timeout or network problem: stored as `unavailable`."""


class VerificationProvider(Protocol):
    name: str
    model: str | None

    def verify(self, request: VerificationRequest) -> VerificationResult: ...
