import uuid
from datetime import datetime

from sqlalchemy import and_, delete, func, or_, select, update
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

    def total_bytes(self, application_id: uuid.UUID) -> int:
        """Every version the application still holds on disk, superseded ones included (US-085)."""
        stmt = select(func.coalesce(func.sum(Document.size_bytes), 0)).where(
            Document.application_id == application_id
        )
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
        self, since: datetime, operator_id: uuid.UUID | None = None, *, exclude_reason: str | None = None
    ) -> int:
        """Verification runs requested since `since`, for one applicant's documents or for everyone
        (US-058 quotas: the cost ceiling is counted in the database, so it holds across restarts).
        Runs stored with `exclude_reason` (the quota refusals themselves) are not counted, otherwise a
        refused attempt would extend the applicant's lock-out by another day."""
        stmt = select(func.count()).select_from(VerificationRun).where(VerificationRun.created_at >= since)
        if exclude_reason is not None:
            stmt = stmt.where(
                or_(VerificationRun.error_reason.is_(None), VerificationRun.error_reason != exclude_reason)
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
