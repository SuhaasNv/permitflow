"""Revision compare (FR-022, FR-023): any two revisions of an application the caller may read."""

import uuid
from typing import Any

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.errors import NotFound
from app.domain.diff import DocumentRef, diff_documents, diff_forms
from app.domain.enums import DocumentType
from app.models import Application, ApplicationRevision, User
from app.repositories.applications import ApplicationRepository
from app.repositories.documents import DocumentRepository
from app.repositories.revisions import RevisionRepository


class FieldChangeOut(BaseModel):
    key: str
    label: str
    old: Any
    new: Any


class SectionDiffOut(BaseModel):
    key: str
    title: str
    changed: bool
    fields: list[FieldChangeOut]


class DocumentRefOut(BaseModel):
    id: uuid.UUID
    filename: str


class DocumentDiffOut(BaseModel):
    type: str
    label: str
    change: str
    old: DocumentRefOut | None
    new: DocumentRefOut | None


class CompareOut(BaseModel):
    application_id: uuid.UUID
    from_revision: int
    to_revision: int
    sections: list[SectionDiffOut]
    documents: list[DocumentDiffOut]
    changed_section_count: int
    changed_document_count: int


class CompareService:
    def __init__(self, db: Session) -> None:
        self.applications = ApplicationRepository(db)
        self.revisions = RevisionRepository(db)
        self.documents = DocumentRepository(db)

    def compare(self, user: User, application_id: uuid.UUID, from_no: int, to_no: int) -> CompareOut:
        app = self.applications.get_for(user, application_id)
        revisions = {r.revision_number: r for r in self.revisions.list_for(app.id)}
        if from_no not in revisions or to_no not in revisions:
            raise NotFound("Revision not found.")
        return self.build(app, revisions[from_no], revisions[to_no])

    def changed_since_previous(self, app: Application) -> tuple[set[str], set[DocumentType], int | None]:
        """Changed section keys and document types between the current revision and the one before it."""
        revisions = self.revisions.list_for(app.id)
        if len(revisions) < 2:
            return set(), set(), None
        out = self.build(app, revisions[-2], revisions[-1])
        return (
            {s.key for s in out.sections if s.changed},
            {DocumentType(d.type) for d in out.documents if d.change != "unchanged"},
            revisions[-2].revision_number,
        )

    def build(self, app: Application, a: ApplicationRevision, b: ApplicationRevision) -> CompareOut:
        sections = diff_forms(a.form_data, b.form_data)
        documents = diff_documents(self._refs(a), self._refs(b))
        return CompareOut(
            application_id=app.id,
            from_revision=a.revision_number,
            to_revision=b.revision_number,
            sections=[
                SectionDiffOut(
                    key=s.key,
                    title=s.title,
                    changed=s.changed,
                    fields=[FieldChangeOut(key=f.key, label=f.label, old=f.old, new=f.new) for f in s.fields],
                )
                for s in sections
            ],
            documents=[
                DocumentDiffOut(
                    type=d.type.value,
                    label=d.label,
                    change=d.change,
                    old=DocumentRefOut(id=uuid.UUID(d.old.id), filename=d.old.filename) if d.old else None,
                    new=DocumentRefOut(id=uuid.UUID(d.new.id), filename=d.new.filename) if d.new else None,
                )
                for d in documents
            ],
            changed_section_count=sum(1 for s in sections if s.changed),
            changed_document_count=sum(1 for d in documents if d.change != "unchanged"),
        )

    def _refs(self, revision: ApplicationRevision) -> dict[DocumentType, DocumentRef]:
        docs = self.documents.get_many([uuid.UUID(i) for i in revision.document_ids])
        return {
            d.document_type: DocumentRef(id=str(d.id), sha256=d.sha256, filename=d.original_filename)
            for d in docs
        }
