"""US-111: the APP_VERSION environment variable overrides the file literal; the literal is the fallback."""

import importlib
import re
from collections.abc import Iterator
from pathlib import Path

import pytest

from app.core import version

# The line scripts/release_guard.py reads; the release ritual bumps it.
LITERALS = re.findall(
    r'^APP_VERSION\s*=\s*"([^"]+)"\s*$', Path(version.__file__).read_text(encoding="utf-8"), re.MULTILINE
)


@pytest.fixture(autouse=True)
def _restore_version() -> Iterator[None]:
    yield
    importlib.reload(version)


def test_literal_line_stays_matchable_by_the_release_guard() -> None:
    assert len(LITERALS) == 1


def test_literal_is_the_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("APP_VERSION", raising=False)
    assert importlib.reload(version).APP_VERSION == LITERALS[0]
    monkeypatch.setenv("APP_VERSION", "  ")
    assert importlib.reload(version).APP_VERSION == LITERALS[0]


def test_environment_overrides_the_literal(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_VERSION", "9.9.9")
    assert importlib.reload(version).APP_VERSION == "9.9.9"
