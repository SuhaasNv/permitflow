"""The seed script keeps the published demonstration password off the administrator account in production."""

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest

SEED_PATH = Path(__file__).resolve().parents[2] / "scripts" / "seed.py"


def _load_seed() -> ModuleType:
    spec = importlib.util.spec_from_file_location("seed_script", SEED_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


seed = _load_seed()


@pytest.mark.parametrize(
    "environ",
    [
        {},
        {"SEED_ADMIN_PASSWORD": ""},
        {"SEED_ADMIN_PASSWORD": seed.DEMO_PASSWORD},
        {"SEED_PASSWORD": "Something-Else-1!", "SEED_ADMIN_PASSWORD": seed.DEMO_PASSWORD},
    ],
)
def test_production_refuses_a_missing_or_published_admin_password(environ: dict[str, str]) -> None:
    with pytest.raises(SystemExit) as stop:
        seed.resolve_passwords("production", environ)
    assert stop.value.code != 0 and "SEED_ADMIN_PASSWORD" in str(stop.value.code)


def test_production_accepts_a_private_admin_password() -> None:
    shared, admin = seed.resolve_passwords("production", {"SEED_ADMIN_PASSWORD": "a-private-value-7"})
    assert shared == seed.DEMO_PASSWORD and admin == "a-private-value-7"


@pytest.mark.parametrize("app_env", ["development", "test"])
def test_outside_production_the_admin_falls_back_to_the_shared_password(app_env: str) -> None:
    assert seed.resolve_passwords(app_env, {}) == (seed.DEMO_PASSWORD, seed.DEMO_PASSWORD)
    assert seed.resolve_passwords(app_env, {"SEED_PASSWORD": "Local-Only-1!"}) == (
        "Local-Only-1!",
        "Local-Only-1!",
    )
    assert seed.resolve_passwords(app_env, {"SEED_ADMIN_PASSWORD": "admin-only-1"}) == (
        seed.DEMO_PASSWORD,
        "admin-only-1",
    )
