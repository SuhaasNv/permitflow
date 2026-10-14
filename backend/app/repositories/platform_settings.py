import uuid
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models import PlatformSetting
from app.models.base import utcnow


class PlatformSettingsRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def all(self) -> list[PlatformSetting]:
        return list(self.db.scalars(select(PlatformSetting).order_by(PlatformSetting.key)))

    def limit_statement_time(self, timeout: str) -> None:
        """Cap every statement of the current transaction (`SET LOCAL`): the transaction's end lifts it, and
        no other connection or session is touched."""
        self.db.execute(text("SELECT set_config('statement_timeout', :t, true)"), {"t": timeout})

    def get(self, key: str) -> PlatformSetting | None:
        return self.db.get(PlatformSetting, key)

    def lock(self, key: str) -> PlatformSetting | None:
        """Serialise writers of one setting for the rest of the transaction, so two administrators changing
        it at once each see the other's value as the "old" one in the audit row. A transaction-scoped
        advisory lock, not `FOR UPDATE`, because the first write of a key has no row to lock yet."""
        self.db.execute(text("SELECT pg_advisory_xact_lock(hashtext(:k))"), {"k": f"platform_settings:{key}"})
        return self.db.get(PlatformSetting, key, populate_existing=True)

    def upsert(self, key: str, value: Any, *, updated_by: uuid.UUID, reason: str) -> PlatformSetting:
        row = self.db.get(PlatformSetting, key)
        if row is None:
            row = PlatformSetting(key=key, value=value, updated_by=updated_by, reason=reason)
            self.db.add(row)
        else:
            row.value = value
            row.updated_by = updated_by
            row.reason = reason
            row.updated_at = utcnow()
        return row

    def remove(self, row: PlatformSetting) -> None:
        """Back to the environment default: the row goes, nothing else does (the history is the audit)."""
        self.db.delete(row)
        self.db.flush()
