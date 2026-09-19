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
    # Connection pool (US-044): sized for one uvicorn worker serving the demo load; exhaustion is a fast 503.
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_pool_timeout_seconds: int = 5
    test_database_url: str = "postgresql+psycopg://permitflow:permitflow@localhost:5432/permitflow_test"

    jwt_secret: str = ""
    jwt_expires_minutes: int = 480

    cors_origins: str = "http://localhost:3000"

    upload_dir: str = "./data/uploads"
    upload_max_bytes: int = 10 * 1024 * 1024

    login_rate_limit_per_minute: int = 10
    # Request limits per client IP, sliding minute (US-058): every request, and sign-in attempts of any
    # outcome. 0 disables. Single process; the production step is Redis or an edge limit.
    rate_limit_per_minute: int = 240
    login_attempts_per_minute: int = 20
    # Quotas kept in the database, so they hold across restarts and workers (US-058): open drafts per
    # operator, verification runs per applicant per day, and per platform per day (the cost ceiling).
    max_drafts_per_user: int = 20
    ai_runs_per_user_per_day: int = 60
    ai_runs_per_day: int = 1000
    # Comma-separated proxy addresses whose X-Forwarded-For is trusted, or "*" on a platform whose edge
    # proxy is the only thing that can reach the container (Railway, most PaaS).
    trusted_proxies: str = ""

    ai_provider: Literal["mock", "openai"] = "mock"
    openai_api_key: str = ""
    openai_model: str = "gpt-4.1-mini"
    ai_timeout_seconds: int = 30
    ai_confidence_threshold: float = Field(default=0.6, ge=0.0, le=1.0)
    ai_max_text_chars: int = 20_000
    # LangSmith tracing of the OpenAI provider (US-055): off without a key; inputs hidden by default.
    langsmith_api_key: str = ""
    # Regional endpoint: APAC (Sydney) is https://apac.api.smith.langchain.com; region fixed at sign-up.
    langsmith_endpoint: str = "https://api.smith.langchain.com"
    langsmith_project: str = "permitflow"
    langsmith_hide_inputs: bool = True

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def effective_database_url(self) -> str:
        url = self.test_database_url if self.app_env == "test" else self.database_url
        # Managed databases hand out plain postgresql:// URLs; SQLAlchemy needs the driver named.
        if url.startswith("postgresql://"):
            url = "postgresql+psycopg://" + url[len("postgresql://") :]
        return url

    def validate_for_startup(self) -> None:
        """Refuse to start without a real JWT secret outside the test environment (SEC-006)."""
        if self.app_env != "test" and len(self.jwt_secret) < 16:
            raise RuntimeError("JWT_SECRET must be set to at least 16 characters when APP_ENV is not 'test'")


@lru_cache
def get_settings() -> Settings:
    return Settings()
