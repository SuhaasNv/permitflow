"""Officer review queue (FR-015): every submitted application with internal status and work counts."""

from sqlalchemy.orm import Session

from app.domain.enums import ApplicationStatus, SiteVisitStatus, VerificationStatus
from app.domain.labels import officer_label, tone_for
from app.domain.officer_actions import NextAction, is_decided, next_action
from app.repositories.applications import ApplicationRepository
from app.repositories.documents import DocumentRepository
from app.repositories.feedback import FeedbackRepository
from app.repositories.revisions import RevisionRepository
from app.repositories.site_visits import SiteVisitRepository
from app.schemas.officer import QueueItemOut, QueueOut
from app.services.operator_view import LICENCE_TITLE

# Anything that is not a clean "verified" and not still running needs an officer's eyes, including a
# document the checker could not read (the operator is told an officer will look at it).
_ATTENTION = {
    VerificationStatus.ISSUES_FOUND,
    VerificationStatus.NEEDS_REVIEW,
    VerificationStatus.UNREADABLE,
    VerificationStatus.FAILED,
    VerificationStatus.UNAVAILABLE,
}
_CHECKING = {VerificationStatus.PENDING, VerificationStatus.RUNNING}


class OfficerQueueService:
    def __init__(self, db: Session) -> None:
        self.applications = ApplicationRepository(db)
        self.revisions = RevisionRepository(db)
        self.feedback = FeedbackRepository(db)
        self.documents = DocumentRepository(db)
        self.visits = SiteVisitRepository(db)

    def queue(self) -> QueueOut:
        rows = self.applications.list_submitted()
        ids = [app.id for app, _ in rows]
        stats = self.revisions.stats_for(ids)
        latest = self.revisions.latest_for(ids)
        open_counts = self.feedback.open_counts(ids)
        runs = self.documents.latest_runs_for_applications(ids)
        visits = self.visits.current_for_many(ids)

        items: list[QueueItemOut] = []
        for app, applicant in rows:
            action = next_action(app.status)
            visit = visits.get(app.id)
            if app.status == ApplicationStatus.SITE_VISIT_SCHEDULED:
                # While the appointment is being arranged the row says whose move it is (US-084).
                if visit is None:
                    action = NextAction("Propose a visit date", True)
                elif visit.status == SiteVisitStatus.PROPOSED:
                    action = NextAction("Waiting on operator", False)
                elif visit.status == SiteVisitStatus.COUNTER_PROPOSED:
                    action = NextAction("Decide the visit date", True)
            count, first_submitted = stats.get(app.id, (0, None))
            app_runs = runs.get(app.id, [])
            # The submitted form, never the working copy: during a resubmission round `draft_data` holds
            # the operator's unsubmitted edits, which an officer must not see until they are submitted.
            revision = latest.get(app.id)
            form = revision.form_data if revision is not None else app.draft_data
            business = (form.get("business") or {}).get("business_name")
            premises = (form.get("premises") or {}).get("address_line_1")
            items.append(
                QueueItemOut(
                    id=app.id,
                    reference_no=app.reference_no,
                    licence_title=LICENCE_TITLE,
                    business_name=business if isinstance(business, str) and business else None,
                    premises_summary=premises if isinstance(premises, str) and premises else None,
                    applicant_name=applicant.full_name,
                    status=app.status.value,
                    status_label=officer_label(app.status),
                    status_tone=tone_for(app.status),
                    next_action=action.label,
                    officer_turn=action.officer_turn,
                    decided=is_decided(app.status),
                    revision_count=count,
                    open_feedback_count=open_counts.get(app.id, 0),
                    documents_attention=sum(1 for r in app_runs if r.status in _ATTENTION),
                    documents_checking=sum(1 for r in app_runs if r.status in _CHECKING),
                    submitted_at=first_submitted,
                    last_activity_at=app.updated_at,
                )
            )
        return QueueOut(
            items=items,
            officer_turn_count=sum(1 for i in items if i.officer_turn),
            waiting_on_operator_count=sum(1 for i in items if not i.officer_turn and not i.decided),
            decided_count=sum(1 for i in items if i.decided),
        )
