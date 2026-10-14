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


ADMIN = {"SEED_ADMIN_PASSWORD": "a-private-value-7"}
ADMIN_EMAIL = "admin@permitflow.example.sg"
DEMO_EMAILS = {
    "operator@permitflow.example.sg",
    "officer@permitflow.example.sg",
    "officer2@permitflow.example.sg",
}


def _emails(app_env: str, environ: dict[str, str]) -> set[str]:
    return {user[0] for user in seed.seed_users_for(app_env, environ)}


def test_production_seeds_only_the_administrator_by_default() -> None:
    assert _emails("production", dict(ADMIN)) == {ADMIN_EMAIL}


def test_production_refuses_an_explicit_published_demo_password_without_the_opt_in() -> None:
    environ = {**ADMIN, "SEED_PASSWORD": seed.DEMO_PASSWORD}
    with pytest.raises(SystemExit) as stop:
        seed.resolve_passwords("production", environ)
    assert "SEED_PUBLIC_DEMO" in str(stop.value.code)


@pytest.mark.parametrize("flag", ["true", "TRUE", "1", "yes", " true "])
def test_production_public_demo_opt_in_allows_the_published_password(flag: str) -> None:
    environ = {**ADMIN, "SEED_PUBLIC_DEMO": flag}
    assert seed.resolve_passwords("production", environ) == (seed.DEMO_PASSWORD, "a-private-value-7")
    assert _emails("production", environ) == DEMO_EMAILS | {ADMIN_EMAIL}
    explicit = {**environ, "SEED_PASSWORD": seed.DEMO_PASSWORD}
    assert seed.resolve_passwords("production", explicit)[0] == seed.DEMO_PASSWORD


@pytest.mark.parametrize("flag", ["", "false", "0", "no", "maybe"])
def test_production_a_non_true_flag_is_not_an_opt_in(flag: str) -> None:
    environ = {**ADMIN, "SEED_PUBLIC_DEMO": flag}
    assert _emails("production", environ) == {ADMIN_EMAIL}
    with pytest.raises(SystemExit):
        seed.resolve_passwords("production", {**environ, "SEED_PASSWORD": seed.DEMO_PASSWORD})


def test_production_a_private_demo_password_seeds_the_demo_accounts_with_it() -> None:
    environ = {**ADMIN, "SEED_PASSWORD": "Reviewer-Only-9!"}
    assert seed.resolve_passwords("production", environ) == ("Reviewer-Only-9!", "a-private-value-7")
    assert _emails("production", environ) == DEMO_EMAILS | {ADMIN_EMAIL}


@pytest.mark.parametrize("app_env", ["development", "test"])
def test_outside_production_every_account_is_seeded_with_the_defaults(app_env: str) -> None:
    assert _emails(app_env, {}) == DEMO_EMAILS | {ADMIN_EMAIL}
    assert seed.resolve_passwords(app_env, {"SEED_PASSWORD": seed.DEMO_PASSWORD}) == (
        seed.DEMO_PASSWORD,
        seed.DEMO_PASSWORD,
    )
