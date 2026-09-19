"""Test fixtures. Tests run against the real Postgres test database (ADR-002): the schema is
created by the Alembic migrations (so a fresh database is exercised on every run) and every
table is truncated between tests."""

import os
import secrets
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

os.environ["APP_ENV"] = "test"
# No fallback secret exists in the code (SEC-006); the suite signs with a random one per run.
os.environ.setdefault("JWT_SECRET", secrets.token_urlsafe(32))
os.environ.setdefault("UPLOAD_DIR", "./data/test-uploads")
# Tests never call a paid provider, whatever the developer's .env says (the live check is a manual step,
# recorded in docs/07-ai/AI_VERIFICATION_DESIGN.md). Set TEST_LIVE_AI=1 to run the suite against OpenAI.
if os.environ.get("TEST_LIVE_AI") != "1":
    os.environ["AI_PROVIDER"] = "mock"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.core.settings import get_settings  # noqa: E402
from app.infra import db as dbmod  # noqa: E402
from app.main import create_app  # noqa: E402
from app.models import Base  # noqa: E402

BACKEND_DIR = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session", autouse=True)
def migrated_database() -> Iterator[None]:
    settings = get_settings()
    assert settings.app_env == "test"
    env = {**os.environ, "APP_ENV": "test"}
    subprocess.run(
        [sys.executable, "-m", "alembic", "downgrade", "base"],
        cwd=BACKEND_DIR,
        env=env,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=BACKEND_DIR,
        env=env,
        check=True,
        capture_output=True,
    )
    dbmod.reset_engine()
    yield
    dbmod.reset_engine()


@pytest.fixture(autouse=True)
def clean_tables() -> Iterator[None]:
    yield
    engine = dbmod.get_engine()
    tables = ", ".join(f'"{t.name}"' for t in reversed(Base.metadata.sorted_tables))
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE TABLE {tables} RESTART IDENTITY CASCADE"))


@pytest.fixture
def db() -> Iterator[Session]:
    session = dbmod.session_factory()()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client() -> Iterator[TestClient]:
    app = create_app()
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def clean_uploads() -> Iterator[None]:
    yield
    import shutil

    shutil.rmtree(get_settings().upload_dir, ignore_errors=True)
