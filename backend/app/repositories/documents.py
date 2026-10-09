import uuid
from collections.abc import Iterable
from datetime import datetime

from sqlalchemy import String, and_, delete, func, literal_column, or_, select, text, update
from sqlalchemy.orm import Session

from app.models import Application, Document, VerificationRun
from app.models.enums import DocumentType, VerificationStatus


class DocumentRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def current_for(self, application_id: uuid.UUID) -> list[Document]:
        stmt = (
            select(Document)
            .where(Document.application_id == application_id, Document.is_current.is_(True))
            .order_by(Document.uploaded_at.asc())
        )
        return list(self.db.scalars(stmt))

    def total_bytes(self, application_id: uuid.UUID | None = None) -> int:
        """Every version still on disk, superseded ones included (US-085); one application, or all of
        them for the storage gauge (US-089)."""
        stmt = select(func.coalesce(func.sum(Document.size_bytes), 0))
        if application_id is not None:
            stmt = stmt.where(Document.application_id == application_id)
        return int(self.db.scalar(stmt) or 0)

    def current_of_type(self, application_id: uuid.UUID, document_type: DocumentType) -> Document | None:
        stmt = select(Document).where(
            Document.application_id == application_id,
            Document.document_type == document_type,
            Document.is_current.is_(True),
        )
        return self.db.scalar(stmt)

    def get_in_application(self, application_id: uuid.UUID, document_id: uuid.UUID) -> Document | None:
        """Sub-resource check: the document must belong to the application (SEC-002)."""
        return self.db.scalar(
            select(Document).where(Document.id == document_id, Document.application_id == application_id)
        )

    def get_many(self, ids: list[uuid.UUID]) -> list[Document]:
        if not ids:
            return []
        return list(self.db.scalars(select(Document).where(Document.id.in_(ids))))

    def count_runs_ended_with(self, error_reason: str, *, since: datetime) -> int:
        """Checks stored with this reason since a moment (the AI pause switch: how many were stopped)."""
        stmt = select(func.count()).where(
            VerificationRun.error_reason == error_reason, VerificationRun.created_at >= since
        )
        return int(self.db.scalar(stmt) or 0)

    def latest_run(self, document_id: uuid.UUID) -> VerificationRun | None:
        stmt = (
            select(VerificationRun)
            .where(VerificationRun.document_id == document_id)
            .order_by(VerificationRun.created_at.desc())
            .limit(1)
        )
        return self.db.scalar(stmt)

    def latest_runs(self, document_ids: list[uuid.UUID]) -> dict[uuid.UUID, VerificationRun]:
        out: dict[uuid.UUID, VerificationRun] = {}
        if not document_ids:
            return out
        stmt = (
            select(VerificationRun)
            .where(VerificationRun.document_id.in_(document_ids))
            .order_by(VerificationRun.created_at.asc())
        )
        for run in self.db.scalars(stmt):
            out[run.document_id] = run  # ascending order: the last one wins
        return out

    def all_for(self, application_id: uuid.UUID) -> list[Document]:
        """Every document row of an application, replaced ones included (draft deletion)."""
        return list(self.db.scalars(select(Document).where(Document.application_id == application_id)))

    def purge_for_application(self, application_id: uuid.UUID) -> list[str]:
        """Delete every document and verification run of a draft (US-045); returns the stored keys so
        the caller can remove the files after the commit. Only drafts are ever deleted (SCOPE.md 14)."""
        docs = self.all_for(application_id)
        if docs:
            ids = [d.id for d in docs]
            self.db.execute(delete(VerificationRun).where(VerificationRun.document_id.in_(ids)))
            self.db.execute(delete(Document).where(Document.application_id == application_id))
        return [d.stored_key for d in docs]

    def claim_run(self, run_id: uuid.UUID, started_at: datetime) -> bool:
        """Atomic pending-to-running claim: true for exactly one caller per run."""
        result = self.db.execute(
            update(VerificationRun)
            .where(VerificationRun.id == run_id, VerificationRun.status == VerificationStatus.PENDING)
            .values(status=VerificationStatus.RUNNING, started_at=started_at)
        )
        return int(getattr(result, "rowcount", 0) or 0) == 1

    def fail_interrupted_runs(self, running_before: datetime, finished_at: datetime) -> int:
        """Runs still `running` since before `running_before`, and every `pending` run, become
        `failed: interrupted` (startup after a restart); returns how many."""
        result = self.db.execute(
            update(VerificationRun)
            .where(
                or_(
                    and_(
                        VerificationRun.status == VerificationStatus.RUNNING,
                        VerificationRun.started_at < running_before,
                    ),
                    VerificationRun.status == VerificationStatus.PENDING,
                )
            )
            .values(status=VerificationStatus.FAILED, error_reason="interrupted", finished_at=finished_at)
        )
        return int(getattr(result, "rowcount", 0) or 0)

    # ---- the work queue (US-098, ADR-016): `pending` is queued, `running` is leased ----

    def claim_next(self, worker_id: str, now: datetime, lease_until: datetime) -> uuid.UUID | None:
        """Atomically take the oldest queued run: one statement, so two workers never get the same one.
        `SKIP LOCKED` lets a second worker pass over a row the first is claiming; LIMIT stays inside the
        subquery. The caller commits at once: the claim is held by the lease, not by a transaction."""
        # The status is inlined, not bound, so Postgres can match the partial index
        # `ix_verification_runs_queued` (a generic plan with a bound parameter cannot).
        pending = literal_column(f"'{VerificationStatus.PENDING.value}'", String)
        oldest = (
            select(VerificationRun.id)
            .where(VerificationRun.status == pending)
            .order_by(VerificationRun.created_at)
            .limit(1)
            .with_for_update(skip_locked=True)
            .scalar_subquery()
        )
        stmt = (
            update(VerificationRun)
            .where(VerificationRun.id == oldest)
            .values(
                status=VerificationStatus.RUNNING,
                started_at=now,
                lease_until=lease_until,
                worker_id=worker_id,
                attempts=VerificationRun.attempts + 1,
            )
            .returning(VerificationRun.id)
            .execution_options(synchronize_session=False)
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def release_lease(self, run_id: uuid.UUID, worker_id: str) -> bool:
        """A worker shutting down hands its unfinished run back to the queue; the interrupted attempt does
        not count."""
        result = self.db.execute(
            update(VerificationRun)
            .where(
                VerificationRun.id == run_id,
                VerificationRun.status == VerificationStatus.RUNNING,
                VerificationRun.worker_id == worker_id,
            )
            .values(
                status=VerificationStatus.PENDING,
                lease_until=None,
                worker_id=None,
                attempts=VerificationRun.attempts - 1,
            )
        )
        return int(getattr(result, "rowcount", 0) or 0) == 1

    def reap_expired(self, now: datetime, max_attempts: int) -> tuple[int, list[uuid.UUID]]:
        """Runs whose lease has expired: back to the queue, or `dead` once they have been claimed
        `max_attempts` times. Returns how many were requeued and the ids that died."""
        expired = and_(
            VerificationRun.status == VerificationStatus.RUNNING, VerificationRun.lease_until < now
        )
        dead = self.db.execute(
            update(VerificationRun)
            .where(expired, VerificationRun.attempts >= max_attempts)
            .values(
                status=VerificationStatus.DEAD,
                error_reason="worker_gave_up",
                finished_at=now,
                lease_until=None,
                worker_id=None,
            )
            .returning(VerificationRun.id)
            .execution_options(synchronize_session=False)
        )
        dead_ids = list(dead.scalars())
        requeued = self.db.execute(
            update(VerificationRun)
            .where(expired)
            .values(status=VerificationStatus.PENDING, lease_until=None, worker_id=None)
        )
        return int(getattr(requeued, "rowcount", 0) or 0), dead_ids

    def lock_state(self, run_id: uuid.UUID) -> tuple[VerificationStatus, str | None] | None:
        """Lock the run row and read who holds it, without touching the loaded object: the guard before a
        worker writes its result. None when the run no longer exists (the draft was deleted)."""
        row = self.db.execute(
            select(VerificationRun.status, VerificationRun.worker_id)
            .where(VerificationRun.id == run_id)
            .with_for_update()
        ).first()
        return None if row is None else (row[0], row[1])

    def lifecycle(self, run_id: uuid.UUID) -> str:
        """`ok` while the run's application and document exist and the document is the current revision,
        `replaced` when a newer revision superseded it, `removed` when the draft or document is gone."""
        current = self.db.execute(
            select(Document.is_current)
            .select_from(VerificationRun)
            .join(Document, Document.id == VerificationRun.document_id)
            .join(Application, Application.id == Document.application_id)
            .where(VerificationRun.id == run_id)
        ).scalar_one_or_none()
        if current is None:
            return "removed"
        return "ok" if current else "replaced"

    def notify_queue(self) -> None:
        """Wake the workers (`LISTEN verification_runs`). Polling covers a missed notification."""
        self.db.execute(text("SELECT pg_notify('verification_runs', '')"))

    def queue_stats(self, now: datetime) -> tuple[int, float, int, int]:
        """Queue depth, age in seconds of the oldest queued run (0 when none), active leases, dead runs."""
        depth, oldest = self.db.execute(
            select(func.count(), func.min(VerificationRun.created_at)).where(
                VerificationRun.status == VerificationStatus.PENDING
            )
        ).one()
        leases = self.db.scalar(
            select(func.count()).where(
                VerificationRun.status == VerificationStatus.RUNNING, VerificationRun.lease_until > now
            )
        )
        dead = self.db.scalar(select(func.count()).where(VerificationRun.status == VerificationStatus.DEAD))
        age = (now - oldest).total_seconds() if oldest is not None else 0.0
        return int(depth), age, int(leases or 0), int(dead or 0)

    def add(self, doc: Document) -> Document:
        self.db.add(doc)
        return doc

    def runs_since(self, since: datetime, until: datetime) -> list[VerificationRun]:
        """Every run created in a window (the admin health block, US-070)."""
        stmt = select(VerificationRun).where(
            VerificationRun.created_at >= since, VerificationRun.created_at < until
        )
        return list(self.db.scalars(stmt))

    def count_runs_since(
        self,
        since: datetime,
        operator_id: uuid.UUID | None = None,
        *,
        exclude_reasons: Iterable[str] = (),
    ) -> int:
        """Verification runs requested since `since`, for one applicant's documents or for everyone
        (US-058 quotas: the cost ceiling is counted in the database, so it holds across restarts).
        Runs stored with one of `exclude_reasons` (the quota refusals themselves, and checks held back by
        the pause switch) are not counted, otherwise a refused attempt would extend the applicant's
        lock-out by another day."""
        stmt = select(func.count()).select_from(VerificationRun).where(VerificationRun.created_at >= since)
        excluded = list(exclude_reasons)
        if excluded:
            stmt = stmt.where(
                or_(VerificationRun.error_reason.is_(None), VerificationRun.error_reason.not_in(excluded))
            )
        if operator_id is not None:
            stmt = (
                stmt.join(Document, Document.id == VerificationRun.document_id)
                .join(Application, Application.id == Document.application_id)
                .where(Application.operator_id == operator_id)
            )
        return int(self.db.execute(stmt).scalar_one())

    def add_run(self, run: VerificationRun) -> VerificationRun:
        self.db.add(run)
        return run

    def present_types_for(self, application_ids: list[uuid.UUID]) -> dict[uuid.UUID, set[DocumentType]]:
        """Current document types per application, one query."""
        if not application_ids:
            return {}
        stmt = select(Document.application_id, Document.document_type).where(
            Document.application_id.in_(application_ids), Document.is_current.is_(True)
        )
        out: dict[uuid.UUID, set[DocumentType]] = {}
        for app_id, dtype in self.db.execute(stmt):
            out.setdefault(app_id, set()).add(dtype)
        return out

    def latest_runs_for_applications(
        self, application_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, list[VerificationRun]]:
        """Latest verification run of every current document, grouped by application (officer queue)."""
        if not application_ids:
            return {}
        docs = list(
            self.db.scalars(
                select(Document).where(
                    Document.application_id.in_(application_ids), Document.is_current.is_(True)
                )
            )
        )
        runs = self.latest_runs([d.id for d in docs])
        out: dict[uuid.UUID, list[VerificationRun]] = {}
        for d in docs:
            run = runs.get(d.id)
            if run is not None:
                out.setdefault(d.application_id, []).append(run)
        return out
