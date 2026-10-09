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
    # US-093: a session unseen for this long ends by itself, so a device left signed in on site never
    # locks the account. Sign-in and every request refresh "seen"; the token's own expiry is unchanged.
    session_idle_minutes: int = 60

    cors_origins: str = "http://localhost:3000"

    upload_dir: str = "./data/uploads"
    upload_max_bytes: int = 10 * 1024 * 1024
    # US-085: everything one application holds on the volume (every document version, clarification
    # evidence, the licence). A 5 GB volume holds about 34 applications at the ceiling; most use a tenth.
    storage_budget_bytes: int = 150 * 1024 * 1024

    # US-097: where uploaded files live. `local` is the disk under UPLOAD_DIR (the default, today's
    # behaviour); `s3` is an S3-compatible bucket (a Railway bucket, MinIO locally). No credential has a
    # default: with `s3` the four below that are marked required must be set or the app refuses to start.
    storage_backend: Literal["local", "s3"] = "local"
    s3_endpoint_url: str = ""  # empty = AWS; MinIO or a Railway bucket name theirs
    s3_bucket: str = ""  # required with `s3`
    s3_region: str = "us-east-1"
    s3_access_key_id: str = ""  # required with `s3`
    s3_secret_access_key: str = ""  # required with `s3`
    s3_addressing_style: Literal["auto", "path", "virtual"] = "auto"  # MinIO needs `path`

    # US-098: image decode memory and the platform-wide stored-bytes ceiling. At most this many images are
    # decoded and re-encoded at once in this process (a 40 MP image is hundreds of MB while it is open);
    # a caller waits a bounded time, then gets a 503. The total ceiling counts every stored document
    # version and clarification attachment, on either backend; 0 means no ceiling and is refused in
    # production (the gauge `permitflow_storage_bytes{kind="limit"}` and the 80 % alert read it).
    image_decode_concurrency: int = Field(default=2, ge=1)
    storage_total_max_bytes: int = Field(default=5 * 1024**3, ge=0)

    # Mark site visit done and the checklist submit wait for the visit day (Singapore date; UAT run 5, F12).
    # Off only where a whole appointment must run in one sitting: the automated suites and a demonstration.
    site_visit_day_guard: bool = True

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
    # The header the trusted edge writes with the connecting client's address, read before
    # X-Forwarded-For (Railway: X-Real-IP). Ignored without a trusted proxy; empty disables it (US-082).
    client_ip_header: str = "X-Real-IP"

    ai_provider: Literal["mock", "openai"] = "mock"
    openai_api_key: str = ""
    openai_model: str = "gpt-4.1-mini"
    ai_timeout_seconds: int = 30
    ai_confidence_threshold: float = Field(default=0.6, ge=0.0, le=1.0)
    ai_max_text_chars: int = 20_000
    # LangSmith tracing of the OpenAI provider (US-055): off without a key; inputs hidden by default.
    langsmith_api_key: str = ""
    # US-077: `/metrics` is served only when a token is set; Prometheus presents it as a bearer token.
    metrics_token: str = ""
    # Regional endpoint: APAC (Sydney) is https://apac.api.smith.langchain.com; region fixed at sign-up.
    langsmith_endpoint: str = "https://api.smith.langchain.com"
    langsmith_project: str = "permitflow"
    langsmith_hide_inputs: bool = True

    # US-101: the limits above are the defaults and the hard ceilings of the admin settings panel. The
    # worker's concurrency (US-098) is a panel setting too, so its ceiling lives here.
    worker_concurrency: int = 2
    # US-101: the API announces every settings change in the Telegram chat the monitoring bot already
    # uses. Both empty: no message and no network call.
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    # US-098 (ADR-016): where document checks run. `inline` is the API process (FastAPI background tasks,
    # the default); `worker` queues the run in `verification_runs` and `python -m app.worker` executes it.
    verification_mode: Literal["inline", "worker"] = "inline"
    # Worker only. The lease is how long a claimed run may go without finishing before the reaper takes it
    # back; it must exceed the PDF deadline plus the model timeout. The metrics port is private (no
    # published port, not routed by the edge). Postgres drops a lock wait after the lock timeout.
    worker_lease_seconds: int = 180
    worker_metrics_port: int = 9100
    worker_lock_timeout_seconds: int = 5
    # Both modes: the PDF text extraction runs in a child process killed at the wall-clock deadline, with
    # address-space and CPU-time caps (a hostile or broken PDF cannot take the API or the worker with it).
    # The CPU cap sits above the page budget (10 s) so a slow but legitimate PDF is cut by the budget and
    # keeps the text read so far, rather than killed by the cap with nothing; the wall clock sits above both.
    pdf_extract_timeout_seconds: float = Field(default=25.0, ge=2.0)
    pdf_extract_memory_mb: int = Field(default=512, ge=64)
    pdf_extract_cpu_seconds: int = Field(default=20, ge=2)

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
        """Refuse to start without a real JWT secret in every environment, tests included (SEC-006). The
        placeholder from `.env.example` counts as unset."""
        if len(self.jwt_secret) < 16 or self.jwt_secret == "change-me-to-a-long-random-string":
            raise RuntimeError("JWT_SECRET must be set to at least 16 random characters")
        if self.app_env == "production" and self.storage_total_max_bytes <= 0:
            raise RuntimeError("STORAGE_TOTAL_MAX_BYTES must be above 0 in production")
        if (
            self.app_env == "production"
            and self.verification_mode == "worker"
            and self.storage_backend == "local"
        ):
            # A separate worker service cannot read the API's volume (ADR-015): every check would fail.
            raise RuntimeError("VERIFICATION_MODE=worker needs STORAGE_BACKEND=s3 in production")
        if self.worker_lease_seconds <= self.pdf_extract_timeout_seconds + 2 * self.ai_timeout_seconds:
            # A lease shorter than the longest check lets the reaper take back a run that is still working.
            raise RuntimeError(
                "WORKER_LEASE_SECONDS must exceed PDF_EXTRACT_TIMEOUT_SECONDS + 2 * AI_TIMEOUT_SECONDS"
            )
        if self.storage_backend == "s3" and self.s3_missing():
            raise RuntimeError(f"STORAGE_BACKEND=s3 needs {', '.join(self.s3_missing())} to be set")

    def s3_missing(self) -> list[str]:
        """The required bucket settings that are empty (US-097)."""
        required = {
            "S3_BUCKET": self.s3_bucket,
            "S3_ACCESS_KEY_ID": self.s3_access_key_id,
            "S3_SECRET_ACCESS_KEY": self.s3_secret_access_key,
        }
        return [name for name, value in required.items() if not value]


@lru_cache
def get_settings() -> Settings:
    return Settings()
