import pytest

from app.core.settings import Settings


def test_refuses_to_start_without_jwt_secret_outside_test() -> None:
    s = Settings(app_env="development", jwt_secret="short", _env_file=None)  # type: ignore[call-arg]
    with pytest.raises(RuntimeError):
        s.validate_for_startup()


def test_test_env_does_not_require_secret() -> None:
    s = Settings(app_env="test", jwt_secret="", _env_file=None)  # type: ignore[call-arg]
    s.validate_for_startup()


def test_cors_origins_parsed() -> None:
    s = Settings(cors_origins="http://a, http://b ,", _env_file=None)  # type: ignore[call-arg]
    assert s.cors_origin_list == ["http://a", "http://b"]
