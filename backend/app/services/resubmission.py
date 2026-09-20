"""Operator resubmission (FR-011 to FR-013, ADR-007): what the operator may see and change, whether a resubmit
is possible, and the resubmit itself (Revision N+1, feedback addressed, officers notified)."""

import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core import metrics
from app.core.errors import InvalidTransition, ValidationFailed
from app.domain.enums import ApplicationStatus, DocumentType, FeedbackResolution, NotificationKind
from app.domain.form_schema import DOCUMENT_TYPE_LABELS, get_section
from app.domain.operator_errors import refusal
from app.domain.resolution import FeedbackTarget, addressed_items, changed_targets, open_targets
from app.domain.workflow import Actor, TransitionContext, TransitionError, transition
from app.models import Application, ApplicationRevision, Document, User
from app.repositories.applications import ApplicationRepository
from app.repositories.audit import AuditRepository
from app.repositories.documents import DocumentRepository
from app.repositories.feedback import FeedbackRepository
from app.repositories.revisions import RevisionRepository
from app.schemas.applications import OperatorFeedbackView, ResubmitReadiness
from app.services.feedback import target_label
from app.services.notifications import NotificationService


class ResubmissionService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.applications = ApplicationRepository(db)
        self.documents = DocumentRepository(db)
        self.revisions = RevisionRepository(db)
        self.feedback = FeedbackRepository(db)
        self.audit = AuditRepository(db)
        self.notifications = NotificationService(db)

    # ---------- read side ----------

    def released_feedback(self, app: Application) -> list[OperatorFeedbackView]:
        """Only items the officer released; drafts and pre-release withdrawals never reach the operator."""
        revisions = {r.id: r.revision_number for r in self.revisions.list_for(app.id)}
        out: list[OperatorFeedbackView] = []
        for f in self.feedback.list_for(app.id):
            if f.released_to_operator_at is None or f.resolution == FeedbackResolution.WITHDRAWN:
                continue
            out.append(
                OperatorFeedbackView(
                    id=f.id,
                    target_type=f.target_type.value,
                    section_key=f.section_key,
                    document_type=f.document_type.value if f.document_type else None,
                    target_label=target_label(f),
                    message=f.message,
                    resolution=f.resolution.value,
                    round=revisions.get(f.raised_in_revision_id, 0),
                    released_at=f.released_to_operator_at,
                    addressed_in_revision=(
                        revisions.get(f.addressed_in_revision_id) if f.addressed_in_revision_id else None
                    ),
                )
            )
        return out

    def readiness(self, app: Application, docs: list[Document]) -> ResubmitReadiness | None:
        if app.status != ApplicationStatus.PENDING_PRE_SITE_RESUBMISSION:
            return None
        current = self._current_revision(app)
        if current is None:
            return None
        items = self._open_released(app)
        flagged = open_targets(items)
        changes = changed_targets(
            current.form_data,
            app.draft_data,
            self._doc_hashes(current),
            {d.document_type: d.sha256 for d in docs},
            flagged,
        )
        untouched = [
            *(_section_label(k) for k in sorted(flagged.sections - changes.sections)),
            *(DOCUMENT_TYPE_LABELS[t] for t in flagged.document_types if t not in changes.document_types),
        ]
        return ResubmitReadiness(
            can_resubmit=changes.any,
            changed_sections=sorted(changes.sections),
            changed_document_types=sorted(t.value for t in changes.document_types),
            untouched_targets=untouched,
            reason=None
            if changes.any
            else "Change at least one flagged section or document before resubmitting.",
        )

    # ---------- write side ----------

    def resubmit(self, operator: User, application_id: uuid.UUID) -> Application:
        app = self.applications.get_for(operator, application_id, for_update=True)
        docs = self.documents.current_for(app.id)
        current = self._current_revision(app)
        items = self._open_released(app)
        flagged = open_targets(items)
        changes = (
            changed_targets(
                current.form_data,
                app.draft_data,
                self._doc_hashes(current),
                {d.document_type: d.sha256 for d in docs},
                flagged,
            )
            if current
            else None
        )
        ctx = TransitionContext(has_changes_to_flagged_targets=bool(changes and changes.any))
        try:
            new_status = transition(app.status, ApplicationStatus.PRE_SITE_RESUBMITTED, Actor.OPERATOR, ctx)
        except TransitionError as exc:
            if exc.kind == "guard":
                raise ValidationFailed(exc.message, details={"reason": "no_change"}) from exc
            # Operator bodies never carry internal status codes (FR-026): no `allowed` list, own label only.
            raise InvalidTransition(refusal(app.status, "resubmit")) from exc
        if changes is None:  # pragma: no cover - the guard guarantees a current revision exists
            raise ValidationFailed(
                "Nothing has changed since the last submission.", details={"reason": "no_change"}
            )

        number = self.revisions.next_number(app.id)
        revision = ApplicationRevision(
            application_id=app.id,
            revision_number=number,
            form_data=dict(app.draft_data),
            document_ids=[str(d.id) for d in docs],
            submitted_by=operator.id,
            submitted_at=datetime.now(UTC),
        )
        self.revisions.add(revision)
        self.db.flush()
        addressed = set(addressed_items(items, changes))
        by_id = {str(f.id): f for f in self.feedback.open_for(app.id)}
        for fid in addressed:
            f = by_id.get(fid)
            if f is None:
                continue
            f.resolution = FeedbackResolution.ADDRESSED
            f.addressed_in_revision_id = revision.id
            self.audit.record(
                application_id=app.id,
                actor_id=operator.id,
                event_type="feedback.addressed",
                payload={"feedback_id": fid, "revision_number": number, "target": target_label(f)},
            )
        previous = app.status
        app.status = new_status
        app.current_revision_id = revision.id
        app.version += 1
        self.audit.record(
            application_id=app.id,
            actor_id=operator.id,
            event_type="revision.submitted",
            payload={
                "revision_number": number,
                "revision_id": str(revision.id),
                "changed_sections": sorted(changes.sections),
                "changed_document_types": sorted(t.value for t in changes.document_types),
                "addressed": sorted(addressed),
            },
        )
        self.audit.record(
            application_id=app.id,
            actor_id=operator.id,
            event_type="status.changed",
            payload={"from": previous.value, "to": new_status.value, "trigger": "resubmit"},
        )
        business = (app.draft_data.get("business") or {}).get("business_name") or app.reference_no
        self.notifications.notify_officers(
            app,
            NotificationKind.RESUBMITTED,
            f"Resubmission {app.reference_no}",
            f"{business} · Revision {number} · {len(addressed)} of {len(items)} items addressed",
        )
        self.db.commit()
        metrics.TRANSITIONS.labels(new_status.value, "operator").inc()
        self.notifications.flush_sent()
        self.db.refresh(app)
        return app

    # ---------- helpers ----------

    def _current_revision(self, app: Application) -> ApplicationRevision | None:
        revisions = self.revisions.list_for(app.id)
        return revisions[-1] if revisions else None

    def _open_released(self, app: Application) -> list[FeedbackTarget]:
        return [
            FeedbackTarget(
                id=str(f.id),
                target_type=f.target_type,
                section_key=f.section_key,
                document_type=f.document_type,
            )
            for f in self.feedback.open_for(app.id)
            if f.released_to_operator_at is not None
        ]

    def _doc_hashes(self, revision: ApplicationRevision) -> dict[DocumentType, str]:
        ids = [uuid.UUID(i) for i in revision.document_ids]
        docs = self.documents.get_many(ids)
        return {d.document_type: d.sha256 for d in docs}


def _section_label(key: str) -> str:
    section = get_section(key)
    return section.title if section else key
