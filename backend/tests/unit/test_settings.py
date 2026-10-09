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
            security.create_access_token(uuid.uuid4(), "operator", uuid.uuid4())
    finally:
        get_settings.cache_clear()


def test_production_refuses_to_start_without_a_total_storage_ceiling() -> None:
    base = Settings.model_construct(jwt_secret="x" * 32)

    def check(app_env: str, ceiling: int) -> None:
        base.model_copy(
            update={"app_env": app_env, "storage_total_max_bytes": ceiling}
        ).validate_for_startup()

    check("production", 1)
    check("development", 0)
    with pytest.raises(RuntimeError, match="STORAGE_TOTAL_MAX_BYTES"):
        check("production", 0)


def test_worker_mode_startup_rules() -> None:
    base = Settings.model_construct(jwt_secret="x" * 32, verification_mode="worker")

    def check(**update: object) -> None:
        base.model_copy(update=update).validate_for_startup()

    bucket = {"s3_bucket": "b", "s3_access_key_id": "k", "s3_secret_access_key": "s"}
    check(app_env="production", storage_backend="s3", **bucket)
    check(app_env="development", storage_backend="local")
    with pytest.raises(RuntimeError, match="STORAGE_BACKEND=s3"):
        check(app_env="production", storage_backend="local")
    # The lease must exceed the PDF deadline plus two model timeouts (25 + 2 * 30 = 85 by default).
    check(worker_lease_seconds=86)
    with pytest.raises(RuntimeError, match="WORKER_LEASE_SECONDS"):
        check(worker_lease_seconds=85)


def test_pdf_extract_limits_have_lower_bounds() -> None:
    for field, value in (
        ("pdf_extract_timeout_seconds", 0.5),
        ("pdf_extract_memory_mb", 1),
        ("pdf_extract_cpu_seconds", 0),
    ):
        with pytest.raises(ValueError):
            Settings(_env_file=None, **{field: value})  # type: ignore[call-arg, arg-type]


def test_cors_origins_parsed() -> None:
    s = Settings(cors_origins="http://a, http://b ,", _env_file=None)  # type: ignore[call-arg]
    assert s.cors_origin_list == ["http://a", "http://b"]


def test_plain_postgresql_url_gets_the_psycopg_driver(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("JWT_SECRET", "x" * 32)
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@host:5432/db")
    assert Settings().effective_database_url == "postgresql+psycopg://u:p@host:5432/db"
