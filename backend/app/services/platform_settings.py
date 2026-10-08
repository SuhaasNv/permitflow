"""Platform settings (US-101): the live values every limit reads, and the administrator's changes.

Two classes, one module:

- `LiveSettings` is what the limiter, the quotas, the upload gate and the AI cap read. It keeps the stored
  overrides in memory for ten seconds (an injectable clock makes that testable), falls back to the
  environment when a key has no row, and falls back to the environment for everything when the table
  cannot be read, so a database hiccup never loosens or tightens a limit by surprise. With an empty table
  every value is the environment value: behaviour is what it was before the story.
- `PlatformSettingsService` is the administrator's side: list, change, history, revert. Every write takes
  a per-key lock, checks the bounds in `domain.platform_settings`, writes the override and its audit row
  in one transaction, then (after the commit) drops the local cache and announces the change on Telegram.
  The caller has already re-verified the administrator's password (step-up).
"""

import logging
import threading
import time
import uuid
from collections.abc import Callable
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
from app.infra.db import session_factory
from app.models import PlatformSetting, User
from app.repositories.audit import AuditRepository
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


def _load_rows() -> dict[str, Any]:
    with session_factory()() as db:
        return {row.key: row.value for row in PlatformSettingsRepository(db).all()}


class LiveSettings:
    """The cached read side. Thread-safe; one reload at a time, and only the very first read waits for it."""

    def __init__(
        self,
        *,
        clock: Clock = time.monotonic,
        ttl: float = TTL_SECONDS,
        loader: Callable[[], dict[str, Any]] = _load_rows,
    ) -> None:
        self._clock = clock
        self._ttl = ttl
        self._loader = loader
        self._snapshot: dict[str, Any] = {}
        self._loaded_at: float | None = None
        self._lock = threading.Lock()

    def invalidate(self) -> None:
        """Forget the snapshot: the next read reloads. Called after a write in this process; the other
        processes pick the change up within the ttl."""
        self._loaded_at = None

    def _rows(self) -> dict[str, Any]:
        loaded = self._loaded_at
        if loaded is not None and self._clock() - loaded < self._ttl:
            return self._snapshot
        # Only the first read (nothing to serve yet) waits; afterwards one thread reloads and the rest
        # keep serving the previous snapshot, so a slow database never stalls the request path.
        if not self._lock.acquire(blocking=loaded is None):
            return self._snapshot
        try:
            now = self._clock()
            if self._loaded_at is not None and now - self._loaded_at < self._ttl:
                return self._snapshot
            try:
                self._snapshot = self._loader()
            except Exception:  # noqa: BLE001 - settings must never take the request path down
                logger.warning("platform_settings_unreadable", exc_info=True)
            self._loaded_at = now
            return self._snapshot
        finally:
            self._lock.release()

    def value(self, key: str) -> Value:
        spec = spec_for(key)
        settings = get_settings()
        env = getattr(settings, spec.env_field) if spec.env_field else None
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
        if new == old and type(new) is type(old):
            self.db.rollback()
            raise ValidationFailed(
                f"{spec.label} is already {_show(old)}.",
                details={"key": spec.key, "reason": "no_change"},
            )
        if restore_default:
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
        if reverted_event_id is not None:
            payload["reverted_event_id"] = str(reverted_event_id)
        self.audit.record(application_id=None, actor_id=admin.id, event_type=event_type, payload=payload)
        self.db.commit()
        # After the commit: a rolled-back change is never announced, and the local cache is dropped so this
        # process serves the new value at once (the others within the ttl).
        live().invalidate()
        notifier.notify(
            f"PermitFlow [{settings.app_env}] setting {'reverted' if reverted_event_id else 'changed'}\n"
            f"{spec.label}: {_show(old)} -> {_show(new)}\n"
            f"By {admin.full_name}\nReason: {reason}"
        )
        fresh = self.repo.get(spec.key)
        names = self.users.names([admin.id])
        return self._out(spec, fresh, names)

    def _env(self, spec: SettingSpec) -> Any:
        return getattr(get_settings(), spec.env_field) if spec.env_field else None

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
