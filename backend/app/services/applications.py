"""Application use cases for operators: create, list, read."""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.core.errors import Forbidden, NotFound, ValidationFailed
from app.domain.editability import editable_targets
from app.domain.form_schema import get_section, validate_section
from app.models import Application, Document, User, VerificationRun
from app.models.enums import ApplicationStatus, DocumentType, LicenceType
from app.repositories.applications import ApplicationRepository
from app.repositories.audit import AuditRepository
from app.repositories.documents import DocumentRepository
from app.repositories.feedback import FeedbackRepository
from app.repositories.revisions import RevisionRepository
from app.services.quotas import ensure_draft_capacity


class ApplicationService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.applications = ApplicationRepository(db)
        self.audit = AuditRepository(db)
        self.documents = DocumentRepository(db)
        self.revisions = RevisionRepository(db)
        self.feedback = FeedbackRepository(db)

    def create(self, operator: User) -> Application:
        """One transaction: application row + `application.created` audit event (AUD-005)."""
        ensure_draft_capacity(self.db, operator.id)
        app = Application(
            reference_no=self.applications.next_reference_no(datetime.now(UTC).year),
            operator_id=operator.id,
            licence_type=LicenceType.FOOD_ESTABLISHMENT,
            status=ApplicationStatus.DRAFT,
            draft_data={},
        )
        self.applications.add(app)
        self.db.flush()
        self.audit.record(
            application_id=app.id,
            actor_id=operator.id,
            event_type="application.created",
            payload={"reference_no": app.reference_no, "licence_type": app.licence_type.value},
        )
        self.db.commit()
        self.db.refresh(app)
        return app

    def list_for(self, operator: User) -> list[Application]:
        return self.applications.list_for_operator(operator.id)

    def get_for(self, user: User, application_id: uuid.UUID) -> Application:
        return self.applications.get_for(user, application_id)

    def update_section(
        self, operator: User, application_id: uuid.UUID, key: str, data: dict[str, Any]
    ) -> Application:
        """Save one section of the working copy (FR-002, FR-003).

        The row is locked for the transaction; editability follows the state machine (403 outside the
        editable set); format/type errors are 422 with per-field messages; in `draft`, missing required
        fields are tolerated so a partial section can be saved and completed later.
        """
        if get_section(key) is None:
            raise NotFound("Section not found.")
        app = self.applications.get_for(operator, application_id, for_update=True)
        sections, _ = self.editable_for(app)
        if key not in sections:
            if app.status == ApplicationStatus.PENDING_PRE_SITE_RESUBMISSION:
                raise Forbidden("The licensing officer did not ask for changes to this section.")
            raise Forbidden("This section is not open for changes.")
        errors = validate_section(key, data, allow_missing=app.status == ApplicationStatus.DRAFT)
        if errors:
            raise ValidationFailed("Some fields need attention.", details={"fields": errors})
        draft = dict(app.draft_data)
        previous = draft.get(key) or {}
        data = dict(data)
        if key == "declarations" and app.status == ApplicationStatus.PENDING_PRE_SITE_RESUBMISSION:
            # A fresh confirmation is the change the officer asked for; the values themselves cannot differ.
            data["confirmed_at"] = datetime.now(UTC).isoformat(timespec="seconds")
        changed = sorted(k for k in set(previous) | set(data) if previous.get(k) != data.get(k))
        draft[key] = data
        app.draft_data = draft
        app.version += 1
        # Field names only, never values: the officer can see who changed what, the audit stays free of PII.
        self.audit.record(
            application_id=app.id,
            actor_id=operator.id,
            event_type="section.updated",
            payload={"section": key, "fields": changed},
        )
        self.db.commit()
        self.db.refresh(app)
        return app

    def open_feedback_targets(self, app: Application) -> tuple[set[str], set[DocumentType]]:
        """Section keys and document types with open, released feedback (what the operator may edit)."""
        sections: set[str] = set()
        doc_types: set[DocumentType] = set()
        for item in self.feedback.open_for(app.id):
            if item.released_to_operator_at is None:
                continue
            if item.section_key:
                sections.add(item.section_key)
            if item.document_type is not None:
                doc_types.add(item.document_type)
        return sections, doc_types

    def editable_for(self, app: Application) -> tuple[set[str], set[DocumentType]]:
        sections, doc_types = self.open_feedback_targets(app)
        return editable_targets(app.status, sections, doc_types)

    def documents_with_runs(self, app: Application) -> list[tuple[Document, VerificationRun | None]]:
        docs = self.documents.current_for(app.id)
        runs = self.documents.latest_runs([d.id for d in docs])
        return [(d, runs.get(d.id)) for d in docs]

    def list_stats(
        self, apps: list[Application]
    ) -> tuple[dict[uuid.UUID, set[DocumentType]], dict[uuid.UUID, int]]:
        """Present document types and revision counts for a list, in two queries instead of three per row."""
        ids = [a.id for a in apps]
        present = self.documents.present_types_for(ids)
        revisions = {k: v[0] for k, v in self.revisions.stats_for(ids).items()}
        return present, revisions

    def revision_count(self, app: Application) -> int:
        return self.revisions.count_for(app.id)
