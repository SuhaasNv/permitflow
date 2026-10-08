"""Platform settings (US-101): the live values every limit reads, and the administrator's changes.

Two classes, one module:

- `LiveSettings` is what the limiter, the quotas, the upload gate and the AI cap read. It keeps the stored
  overrides in memory for ten seconds (an injectable clock makes that testable) and falls back to the
  environment when a key has no row. Reading never waits on the database: when the snapshot is due, the
  caller is handed the current one (the environment values only before the first load) and one background
  daemon thread reloads it, on a private connection with a 3 second connect timeout and a 1 second
  statement timeout. A failed reload keeps the last good snapshot (the environment values only before the
  first load) and is not retried for another ten seconds, so a database hiccup never loosens or tightens a
  limit by surprise. With an empty table every value is the environment value: behaviour is what it was
  before the story. A write bumps a generation, so a reload that started before it can never store its
  older rows as fresh.
- `PlatformSettingsService` is the administrator's side: list, change, history, revert. Every write takes
  a per-key lock, checks the bounds in `domain.platform_settings`, writes the override and its audit row
  in one transaction, then (after the commit) refreshes the local cache and announces the change on
  Telegram. The caller has already re-verified the administrator's password (step-up).
"""

import logging
import threading
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.core.errors import NotFound, ValidationFailed
from app.core.settings import get_settings
from app.domain.platform_settings import (
    SPECS,
    SettingRejected,
    SettingSpec,
    UnknownSetting,
    bounds_for,
    default_for,
    effective,
    spec_for,
    validate,
)
from app.infra import notifier
from app.infra.db import background_session
from app.models import PlatformSetting, User
from app.repositories.audit import AuditRepository
from app.repositories.documents import DocumentRepository
from app.repositories.platform_settings import PlatformSettingsRepository
from app.repositories.users import UserRepository
from app.schemas.platform_settings import (
    SettingHistoryEntryOut,
    SettingOut,
    SettingsHistoryOut,
    SettingsOut,
)
from app.services.admin_feed import decode_cursor, encode_cursor

logger = logging.getLogger("permitflow.settings")

TTL_SECONDS = 10.0
CHANGED = "settings.changed"
REVERTED = "settings.reverted"
HISTORY_TYPES = (CHANGED, REVERTED)
MAX_HISTORY_LIMIT = 100

Clock = Callable[[], float]
Value = int | bool | str


LOAD_STATEMENT_TIMEOUT = "1s"


def _load_rows() -> dict[str, Any]:
    with background_session() as db:
        repo = PlatformSettingsRepository(db)
        repo.limit_statement_time(LOAD_STATEMENT_TIMEOUT)
        return {row.key: row.value for row in repo.all()}


def _start_thread(job: Callable[[], None]) -> None:
    threading.Thread(target=job, name="platform-settings-reload", daemon=True).start()


def run_inline(job: Callable[[], None]) -> None:
    """Tests: run the reload on the calling thread, so a read sees the rows it just wrote."""
    job()


@dataclass(frozen=True)
class _Snapshot:
    rows: dict[str, Any]
    loaded_at: float
    generation: int


class LiveSettings:
    """The cached read side. Thread-safe and non-blocking: a read never waits for the database."""

    def __init__(
        self,
        *,
        clock: Clock = time.monotonic,
        ttl: float = TTL_SECONDS,
        loader: Callable[[], dict[str, Any]] = _load_rows,
        spawn: Callable[[Callable[[], None]], None] = _start_thread,
    ) -> None:
        self._clock = clock
        self._ttl = ttl
        self._loader = loader
        self._spawn = spawn
        self._snapshot: _Snapshot | None = None
        self._generation = 0
        self._state_lock = threading.Lock()  # guards `_snapshot` and `_generation`; never held over I/O
        self._reload_lock = threading.Lock()  # held by the one reload in flight

    def invalidate(self) -> None:
        """Mark the snapshot stale: the next read starts a reload, and a reload already running (it began
        before this change) is discarded when it finishes. Called after a write in this process; the other
        processes pick the change up within the ttl."""
        with self._state_lock:
            self._generation += 1

    def refresh(self) -> None:
        """Reload now, on the calling thread. For the write path (a worker thread, never the event loop),
        right after `invalidate()`, so this process serves the new value at once. A failure is logged and
        leaves the previous snapshot in place."""
        with self._state_lock:
            generation = self._generation
        self._load(generation)

    def _is_fresh(self, snap: _Snapshot | None) -> bool:
        return (
            snap is not None
            and snap.generation == self._generation
            and self._clock() - snap.loaded_at < self._ttl
        )

    def _rows(self) -> dict[str, Any]:
        snap = self._snapshot
        if self._is_fresh(snap):
            assert snap is not None
            return snap.rows
        # Due. Serve what there is and let one background thread reload; whoever loses the race for the
        # lock just serves it too. Nothing here waits on the database.
        if self._reload_lock.acquire(blocking=False):
            try:
                self._spawn(self._reload_in_background)
            except Exception:  # noqa: BLE001 - e.g. no thread could be started; try again on a later read
                self._reload_lock.release()
                logger.warning("platform_settings_reload_not_started", exc_info=True)
        snap = self._snapshot
        return snap.rows if snap is not None else {}

    def _reload_in_background(self) -> None:
        try:
            with self._state_lock:
                generation = self._generation
                snap = self._snapshot
            if self._is_fresh(snap):
                return
            self._load(generation)
        finally:
            self._reload_lock.release()

    def _load(self, generation: int) -> None:
        try:
            rows: dict[str, Any] | None = self._loader()
        except Exception:  # noqa: BLE001 - settings must never take the request path down
            logger.warning("platform_settings_unreadable", exc_info=True)
            rows = None
        now = self._clock()
        with self._state_lock:
            if generation != self._generation:
                return  # a change landed while this loaded: these rows may be older than it
            previous = self._snapshot
            kept = rows if rows is not None else (previous.rows if previous is not None else {})
            self._snapshot = _Snapshot(rows=kept, loaded_at=now, generation=generation)

    def value(self, key: str) -> Value:
        spec = spec_for(key)
        settings = get_settings()
        env = _env_value(spec)
        rows = self._rows()
        return effective(spec, rows.get(key), env, settings.app_env, present=key in rows)

    def int_value(self, key: str) -> int:
        v = self.value(key)
        if isinstance(v, bool) or not isinstance(v, int):  # pragma: no cover - the spec is an int
            raise TypeError(f"{key} is not a number")
        return v

    def bool_value(self, key: str) -> bool:
        v = self.value(key)
        if not isinstance(v, bool):  # pragma: no cover - the spec is a switch
            raise TypeError(f"{key} is not a switch")
        return v


_live = LiveSettings()


def live() -> LiveSettings:
    """The process-wide reader. Consumers call this at the moment they need a value, never at import."""
    return _live


def reset_live(replacement: LiveSettings | None = None) -> LiveSettings:
    """Tests: drop the cache, or install a reader with an injected clock or loader."""
    global _live
    _live = replacement if replacement is not None else LiveSettings()
    return _live


def _env_value(spec: SettingSpec) -> int | None:
    """The environment value a setting defaults to and is capped by (None for a setting with no variable)."""
    if spec.env_field is None:
        return None
    value: object = getattr(get_settings(), spec.env_field)
    if isinstance(value, bool) or not isinstance(value, int):  # pragma: no cover - the spec names an int
        raise TypeError(f"{spec.env_field} is not a number")
    return value


def _show(value: Value) -> str:
    if isinstance(value, bool):
        return "on" if value else "off"
    return str(value)


class PlatformSettingsService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = PlatformSettingsRepository(db)
        self.audit = AuditRepository(db)
        self.users = UserRepository(db)
        self.documents = DocumentRepository(db)

    # ---- reads ----

    def overview(self) -> SettingsOut:
        rows = {r.key: r for r in self.repo.all()}
        names = self.users.names(r.updated_by for r in rows.values())
        return SettingsOut(
            settings=[self._out(spec, rows.get(spec.key), names) for spec in SPECS],
            environment=get_settings().app_env,
        )

    def history(self, *, key: str | None, limit: int, before: str | None) -> SettingsHistoryOut:
        if key is not None:
            self._spec(key)
        limit = max(1, min(limit, MAX_HISTORY_LIMIT))
        cursor = decode_cursor(before) if before else None
        events = self.audit.by_type(HISTORY_TYPES, limit=limit + 1, before=cursor, payload_key=key)
        more = len(events) > limit
        events = events[:limit]
        names = self.users.names(e.actor_id for e in events if e.actor_id is not None)
        entries = [
            self._entry(e.id, e.event_type, e.payload, e.actor_id, e.created_at, names) for e in events
        ]
        last = events[-1] if events else None
        return SettingsHistoryOut(
            entries=entries,
            next_cursor=encode_cursor(last.created_at, last.id) if more and last is not None else None,
        )

    def key_of_entry(self, event_id: uuid.UUID) -> str | None:
        """The setting a history entry is about, or None if the id is not a settings entry."""
        event = self.audit.get(event_id)
        if event is None or event.event_type not in HISTORY_TYPES:
            return None
        return str(event.payload.get("key", "")) or None

    # ---- writes ----

    def change(self, admin: User, key: str, value: Value, reason: str) -> SettingOut:
        spec = self._spec(key)
        env = self._env(spec)
        try:
            new = validate(spec, value, env, get_settings().app_env)
        except SettingRejected as exc:
            raise self._invalid(spec, exc) from exc
        return self._write(admin, spec, new, reason, event_type=CHANGED, restore_default=False)

    def revert(self, admin: User, event_id: uuid.UUID, reason: str) -> SettingOut:
        """Undo one change: the setting returns to the value it had before that entry. If it was following
        the environment then, the override goes and it follows the environment again. The value is checked
        against today's bounds, so a revert cannot restore a number the environment ceiling now forbids."""
        event = self.audit.get(event_id)
        if event is None or event.event_type not in HISTORY_TYPES:
            raise NotFound("That history entry does not exist.")
        payload = event.payload
        spec = self._spec(str(payload.get("key", "")))
        was_default = bool(payload.get("old_was_default"))
        env = self._env(spec)
        if was_default:
            return self._write(
                admin,
                spec,
                default_for(spec, env),
                reason,
                event_type=REVERTED,
                restore_default=True,
                reverted_event_id=event.id,
            )
        try:
            old = validate(spec, payload.get("old"), env, get_settings().app_env)
        except SettingRejected as exc:
            raise self._invalid(spec, exc) from exc
        return self._write(
            admin, spec, old, reason, event_type=REVERTED, restore_default=False, reverted_event_id=event.id
        )

    # ---- internals ----

    def _write(
        self,
        admin: User,
        spec: SettingSpec,
        new: Value,
        reason: str,
        *,
        event_type: str,
        restore_default: bool,
        reverted_event_id: uuid.UUID | None = None,
    ) -> SettingOut:
        settings = get_settings()
        env = self._env(spec)
        row = self.repo.lock(spec.key)
        old = effective(spec, row.value if row else None, env, settings.app_env, present=row is not None)
        # A value equal to the environment default is stored as no row, so the panel can always clear an
        # override: "follow the environment" and "set to the same number" are one state.
        default = default_for(spec, env)
        to_default = restore_default or (new == default and type(new) is type(default))
        # Nothing to do when the value is unchanged and there is no stored row to clear.
        if new == old and type(new) is type(old) and (row is None or not to_default):
            self.db.rollback()
            raise ValidationFailed(
                f"{spec.label} is already {_show(old)}.",
                details={"key": spec.key, "reason": "no_change"},
            )
        # Switching the AI back on: say how many checks the pause stopped (known gap until the worker, US-098,
        # holds them in a queue instead). The reason code on a run is the setting's key.
        ended_while_paused: int | None = None
        if spec.key == "ai_paused" and old is True and new is False and row is not None:
            ended_while_paused = self.documents.count_runs_ended_with(spec.key, since=row.updated_at)
        if to_default:
            if row is not None:
                self.repo.remove(row)
        else:
            self.repo.upsert(spec.key, new, updated_by=admin.id, reason=reason)
        payload: dict[str, Any] = {
            "key": spec.key,
            "label": spec.label,
            "old": old,
            "new": new,
            "old_was_default": row is None,
            "reason": reason,
        }
        if ended_while_paused is not None:
            payload["ended_while_paused"] = ended_while_paused
        if reverted_event_id is not None:
            payload["reverted_event_id"] = str(reverted_event_id)
        self.audit.record(application_id=None, actor_id=admin.id, event_type=event_type, payload=payload)
        self.db.commit()
        # After the commit: a rolled-back change is never announced, and the local cache is reloaded here (a
        # worker thread) so this process serves the new value at once (the others within the ttl).
        live().invalidate()
        live().refresh()
        notifier.notify(
            f"PermitFlow [{settings.app_env}] setting {'reverted' if reverted_event_id else 'changed'}\n"
            f"{spec.label}: {_show(old)} -> {_show(new)}\n"
            f"By {admin.full_name}\nReason: {reason}"
            + (
                f"\n{ended_while_paused} checks ended as ai_paused while the AI was paused"
                if ended_while_paused is not None
                else ""
            )
        )
        fresh = self.repo.get(spec.key)
        names = self.users.names([admin.id])
        return self._out(spec, fresh, names)

    def _env(self, spec: SettingSpec) -> int | None:
        return _env_value(spec)

    def _spec(self, key: str) -> SettingSpec:
        try:
            return spec_for(key)
        except UnknownSetting as exc:
            raise NotFound("That setting does not exist.") from exc

    def _invalid(self, spec: SettingSpec, exc: SettingRejected) -> ValidationFailed:
        return ValidationFailed(exc.message, details={"key": spec.key, "reason": exc.reason, **exc.details})

    def _out(
        self, spec: SettingSpec, row: PlatformSetting | None, names: dict[uuid.UUID, tuple[str, str]]
    ) -> SettingOut:
        settings = get_settings()
        env = self._env(spec)
        b = bounds_for(spec, env)
        value = effective(spec, row.value if row else None, env, settings.app_env, present=row is not None)
        choices = list(spec.choices)
        if spec.key == "scanner_fail_mode" and settings.app_env == "production":
            choices = ["closed"]
        return SettingOut(
            key=spec.key,
            label=spec.label,
            description=spec.description,
            group=spec.group,
            kind=spec.kind,
            unit=spec.unit,
            value=value,
            default=default_for(spec, env),
            overridden=row is not None,
            minimum=b.minimum,
            maximum=b.maximum,
            max_source=b.max_source,
            choices=choices,
            in_use=spec.in_use,
            updated_by_name=names.get(row.updated_by, (None, None))[0] if row else None,
            updated_at=row.updated_at if row else None,
            reason=row.reason if row else None,
        )

    def _entry(
        self,
        event_id: uuid.UUID,
        event_type: str,
        payload: dict[str, Any],
        actor_id: uuid.UUID | None,
        at: datetime,
        names: dict[uuid.UUID, tuple[str, str]],
    ) -> SettingHistoryEntryOut:
        reverted = payload.get("reverted_event_id")
        return SettingHistoryEntryOut(
            id=event_id,
            kind="reverted" if event_type == REVERTED else "changed",
            key=str(payload.get("key", "")),
            label=str(payload.get("label", payload.get("key", ""))),
            old=payload.get("old", 0),
            new=payload.get("new", 0),
            old_was_default=bool(payload.get("old_was_default")),
            reason=str(payload.get("reason", "")),
            actor_name=names.get(actor_id, (None, None))[0] if actor_id else None,
            created_at=at,
            reverted_event_id=uuid.UUID(str(reverted)) if reverted else None,
        )
