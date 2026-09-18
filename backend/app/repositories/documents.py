import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Document, VerificationRun
from app.models.enums import DocumentType


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

    def add(self, doc: Document) -> Document:
        self.db.add(doc)
        return doc

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
