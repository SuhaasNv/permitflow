import pytest

from app.core.settings import Settings


@pytest.mark.parametrize("app_env", ["development", "production", "test"])
def test_refuses_to_start_without_a_real_jwt_secret_in_every_environment(app_env: str) -> None:
    for value in ("", "short", "change-me-to-a-long-random-string"):
        s = Settings(app_env=app_env, jwt_secret=value, _env_file=None)  # type: ignore[call-arg]
        with pytest.raises(RuntimeError):
            s.validate_for_startup()


def test_tokens_are_never_signed_with_a_fallback_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    import uuid

    from app.core import security
    from app.core.settings import get_settings

    monkeypatch.setenv("JWT_SECRET", "")
    get_settings.cache_clear()
    try:
        with pytest.raises(RuntimeError):
            security.create_access_token(uuid.uuid4(), "operator")
    finally:
        get_settings.cache_clear()


def test_cors_origins_parsed() -> None:
    s = Settings(cors_origins="http://a, http://b ,", _env_file=None)  # type: ignore[call-arg]
    assert s.cors_origin_list == ["http://a", "http://b"]


def test_plain_postgresql_url_gets_the_psycopg_driver(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("JWT_SECRET", "x" * 32)
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@host:5432/db")
    assert Settings().effective_database_url == "postgresql+psycopg://u:p@host:5432/db"
