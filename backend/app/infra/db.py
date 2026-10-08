"""SQLAlchemy engine and session factory. One request = one session; background tasks open their own."""

from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.settings import get_settings

_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None
_background_engine: Engine | None = None

# The background reader of the platform settings (US-101) must never wait long on a dead or saturated
# database, and must not compete with requests for the application pool: it has a pool of its own.
BACKGROUND_CONNECT_TIMEOUT_SECONDS = 3


def get_engine() -> Engine:
    global _engine, _session_factory
    if _engine is None:
        settings = get_settings()
        _engine = create_engine(
            settings.effective_database_url,
            pool_pre_ping=True,
            future=True,
            pool_size=settings.db_pool_size,
            max_overflow=settings.db_max_overflow,
            pool_timeout=settings.db_pool_timeout_seconds,
        )
        _session_factory = sessionmaker(bind=_engine, expire_on_commit=False, class_=Session)
    return _engine


def session_factory() -> sessionmaker[Session]:
    get_engine()
    if _session_factory is None:  # pragma: no cover - get_engine() creates it
        raise RuntimeError("session factory not initialised")
    return _session_factory


def background_session() -> Session:
    """A session on a small private pool with a short connect timeout, for background readers that run off
    the request path (the live settings reload). The application engine and its defaults are untouched."""
    global _background_engine
    if _background_engine is None:
        settings = get_settings()
        _background_engine = create_engine(
            settings.effective_database_url,
            pool_pre_ping=True,
            future=True,
            pool_size=2,
            max_overflow=0,
            pool_timeout=BACKGROUND_CONNECT_TIMEOUT_SECONDS,
            connect_args={"connect_timeout": BACKGROUND_CONNECT_TIMEOUT_SECONDS},
        )
    return Session(bind=_background_engine, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    db = session_factory()()
    try:
        yield db
    finally:
        db.close()


def database_is_reachable() -> bool:
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:  # noqa: BLE001 - any failure means "not reachable" for the health check
        return False


def reset_engine() -> None:
    """Dispose the cached engine (used by tests when settings change)."""
    global _engine, _session_factory, _background_engine
    if _engine is not None:
        _engine.dispose()
    if _background_engine is not None:
        _background_engine.dispose()
    _engine = None
    _session_factory = None
    _background_engine = None
