"""The administrator's operations overview (US-070, absorbing US-071): counts by status, the idle list,
today's numbers and the document-check health block, all on the Singapore calendar day."""

from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.settings import get_settings
from app.domain.admin import (
    IDLE_LIST_SIZE,
    idle_days,
    is_idle,
    percentile,
    singapore_day_window,
    turn_for,
)
from app.domain.enums import ApplicationStatus, VerificationStatus
from app.domain.labels import officer_label, tone_for
from app.domain.site_visit import today_in_singapore
from app.domain.workflow import TERMINAL
from app.repositories.applications import ApplicationRepository
from app.repositories.audit import AuditRepository
from app.repositories.documents import DocumentRepository
from app.repositories.revisions import RevisionRepository
from app.schemas.admin import (
    AdminOverviewOut,
    ChecksOut,
    IdleApplicationOut,
    StatusCountOut,
    TodayOut,
    TotalsOut,
)

SUBMITTED = {ApplicationStatus.APPLICATION_RECEIVED.value}
RESUBMITTED = {
    ApplicationStatus.PRE_SITE_RESUBMITTED.value,
    ApplicationStatus.POST_SITE_CLARIFICATION_RESUBMITTED.value,
}
PROVIDER_NAMES = {"openai": "OpenAI", "mock": "none (mock)"}


class AdminOverviewService:
    def __init__(self, db: Session) -> None:
        self.applications = ApplicationRepository(db)
        self.audit = AuditRepository(db)
        self.documents = DocumentRepository(db)
        self.revisions = RevisionRepository(db)

    def overview(self, now: datetime | None = None) -> AdminOverviewOut:
        now = now or datetime.now(UTC)
        settings = get_settings()
        by_status = self.applications.count_by_status()
        counts = [
            StatusCountOut(
                status=s.value,
                label=officer_label(s),
                tone=tone_for(s),
                turn=turn_for(s),
                count=by_status.get(s, 0),
            )
            for s in ApplicationStatus
        ]
        idle = self._idle(now)
        totals = TotalsOut(
            applications=sum(c.count for c in counts),
            submitted=sum(c.count for c in counts if c.turn != "draft"),
            drafts=sum(c.count for c in counts if c.turn == "draft"),
            with_office=sum(c.count for c in counts if c.turn == "office"),
            waiting_on_operators=sum(c.count for c in counts if c.turn == "operator"),
            idle_over_7_days=idle[1],
        )
        day = today_in_singapore(now)
        start, end = singapore_day_window(day)
        transitions = self.audit.transitions_since(start, end)
        today = TodayOut(
            day=day.isoformat(),
            submissions=sum(1 for p in transitions if p.get("to") in SUBMITTED),
            resubmissions=sum(1 for p in transitions if p.get("to") in RESUBMITTED),
            checklists_submitted=self.audit.count_since("checklist.submitted", start, end),
            clarification_rounds=self.audit.count_since("clarification.answered", start, end),
            runs_today=self.documents.count_runs_since(start),
            runs_per_day_quota=settings.ai_runs_per_day,
        )
        return AdminOverviewOut(
            as_of=now, totals=totals, counts=counts, idle=idle[0], today=today, checks=self._checks(now)
        )

    def _idle(self, now: datetime) -> tuple[list[IdleApplicationOut], int]:
        """The longest-idle open applications (no audit activity for more than seven Singapore days),
        and how many there are in all."""
        rows = [
            (app, applicant)
            for app, applicant in self.applications.list_submitted()
            if app.status not in TERMINAL
        ]
        ids = [app.id for app, _ in rows]
        last = self.audit.last_activity(ids)
        forms = self.revisions.latest_for(ids)
        found: list[IdleApplicationOut] = []
        for app, _ in rows:
            last_at = last.get(app.id, app.updated_at)
            days = idle_days(last_at, now)
            if not is_idle(days):
                continue
            revision = forms.get(app.id)
            form = revision.form_data if revision is not None else {}
            business = (form.get("business") or {}).get("business_name")
            found.append(
                IdleApplicationOut(
                    id=app.id,
                    reference_no=app.reference_no,
                    business_name=business if isinstance(business, str) and business else None,
                    status=app.status.value,
                    label=officer_label(app.status),
                    tone=tone_for(app.status),
                    days_idle=days,
                    last_activity_at=last_at,
                )
            )
        found.sort(key=lambda i: (-i.days_idle, i.reference_no))
        return found[:IDLE_LIST_SIZE], len(found)

    def _checks(self, now: datetime) -> ChecksOut:
        settings = get_settings()
        runs = self.documents.runs_since(now - timedelta(hours=24), now)
        by = {s: 0 for s in VerificationStatus}
        for r in runs:
            by[r.status] += 1
        latencies = [r.latency_ms / 1000 for r in runs if r.latency_ms is not None]
        average = round(sum(latencies) / len(latencies), 2) if latencies else None
        p95 = percentile(latencies, 0.95)
        provider = PROVIDER_NAMES.get(settings.ai_provider, settings.ai_provider)
        model = settings.openai_model if settings.ai_provider == "openai" else None
        return ChecksOut(
            runs=len(runs),
            verified=by[VerificationStatus.VERIFIED],
            issues_found=by[VerificationStatus.ISSUES_FOUND],
            needs_review=by[VerificationStatus.NEEDS_REVIEW],
            unreadable=by[VerificationStatus.UNREADABLE],
            failed_or_unavailable=by[VerificationStatus.FAILED] + by[VerificationStatus.UNAVAILABLE],
            still_running=by[VerificationStatus.PENDING] + by[VerificationStatus.RUNNING],
            average_seconds=average,
            p95_seconds=round(p95, 2) if p95 is not None else None,
            provider=provider,
            model=model,
        )
