"""Application settings, read once from the environment (NFR-005)."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Repository-root .env first, then a backend-local .env if present (later files win).
    model_config = SettingsConfigDict(
        env_file=(str(Path(__file__).resolve().parents[3] / ".env"), ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: Literal["development", "test", "production"] = "development"
    database_url: str = "postgresql+psycopg://permitflow:permitflow@localhost:5432/permitflow"
    test_database_url: str = "postgresql+psycopg://permitflow:permitflow@localhost:5432/permitflow_test"

    jwt_secret: str = ""
    jwt_expires_minutes: int = 480

    cors_origins: str = "http://localhost:5173"

    upload_dir: str = "./data/uploads"
    upload_max_bytes: int = 10 * 1024 * 1024

    login_rate_limit_per_minute: int = 10

    ai_provider: Literal["mock", "openai"] = "mock"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    ai_timeout_seconds: int = 30
    ai_confidence_threshold: float = Field(default=0.6, ge=0.0, le=1.0)
    ai_max_text_chars: int = 20_000

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def effective_database_url(self) -> str:
        return self.test_database_url if self.app_env == "test" else self.database_url

    def validate_for_startup(self) -> None:
        """Refuse to start without a real JWT secret outside the test environment (SEC-006)."""
        if self.app_env != "test" and len(self.jwt_secret) < 16:
            raise RuntimeError("JWT_SECRET must be set to at least 16 characters when APP_ENV is not 'test'")


@lru_cache
def get_settings() -> Settings:
    return Settings()
