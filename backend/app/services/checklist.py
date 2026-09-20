"""The site visit checklist (US-060, FR-036, FR-037): the officer's inspection record for one visit.
Created on first open while the case is in a site-visit state, saved as a draft, frozen at submit
(US-063). Every mutation locks the application row first (ADR-008); the draft save writes no audit row
because a draft is not a record until it is submitted."""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.errors import Conflict, NotFound, ValidationFailed, VersionConflict
from app.domain.checklist_schema import (
    CHECKLIST_VERSION,
    DESCRIPTION,
    ITEM_BY_KEY,
    ITEM_KEYS,
    ITEMS,
    MAX_COMMENT,
    POSITION,
    SECTIONS,
)
from app.domain.enums import ApplicationStatus, ChecklistResult, ChecklistStatus, ClarificationStatus
from app.domain.workflow import Actor
from app.models import Application, Checklist, ChecklistItem, ClarificationRequest, User
from app.repositories.applications import ApplicationRepository
from app.repositories.audit import AuditRepository
from app.repositories.checklists import ChecklistRepository
from app.repositories.site_visits import SiteVisitRepository
from app.repositories.users import UserRepository
from app.schemas.checklist import (
    ChecklistCounts,
    ChecklistItemDefOut,
    ChecklistItemIn,
    ChecklistItemOut,
    ChecklistOut,
    ChecklistSaveIn,
    ChecklistSchemaOut,
    ChecklistSectionOut,
    ChecklistSummaryOut,
)

SITE_VISIT_STATES = (ApplicationStatus.SITE_VISIT_SCHEDULED, ApplicationStatus.SITE_VISIT_DONE)
SUBMITTED_MESSAGE = "This checklist was submitted; its findings can no longer change."


@dataclass(frozen=True)
class ChecklistFacts:
    """What the workflow guards need to know about the current visit's checklist (US-060, US-063)."""

    started: bool
    complete: bool
    open_clarifications: int
    answered_clarifications: int
    all_open_answered: bool


NO_CHECKLIST = ChecklistFacts(False, False, 0, 0, False)


def schema_out() -> ChecklistSchemaOut:
    return ChecklistSchemaOut(
        version=CHECKLIST_VERSION,
        description=DESCRIPTION,
        sections=[
            ChecklistSectionOut(
                key=s.key,
                title=s.title,
                items=[
                    ChecklistItemDefOut(
                        key=i.key,
                        section=i.section,
                        title=i.title,
                        guidance=i.guidance,
                        applicable_by_default=i.applicable_by_default,
                    )
                    for i in s.items
                ],
            )
            for s in SECTIONS
        ],
        item_count=len(ITEMS),
    )


def counts_for(items: list[ChecklistItem]) -> ChecklistCounts:
    assessed = sum(1 for i in items if i.result != ChecklistResult.NOT_ASSESSED)
    flagged = sum(1 for i in items if i.needs_clarification)
    unsat = sum(1 for i in items if i.result == ChecklistResult.UNSATISFACTORY)
    na = sum(1 for i in items if i.result == ChecklistResult.NOT_APPLICABLE)
    missing = sum(
        1
        for i in items
        if (i.result == ChecklistResult.UNSATISFACTORY or i.needs_clarification)
        and not (i.comment or "").strip()
    )
    return ChecklistCounts(
        total=len(items),
        assessed=assessed,
        flagged=flagged,
        unsatisfactory=unsat,
        not_applicable=na,
        missing_comments=missing,
    )


def remaining_sentence(c: ChecklistCounts) -> str | None:
    """What still blocks a submit, the way the sticky card says it."""
    parts: list[str] = []
    left = c.total - c.assessed
    if left:
        parts.append(f"assess {left} more item{'s' if left != 1 else ''}")
    if c.missing_comments:
        parts.append(f"add {c.missing_comments} comment{'s' if c.missing_comments != 1 else ''}")
    if not parts:
        return None
    joined = " and ".join(parts)
    return joined[0].upper() + joined[1:] + " to submit."


class ChecklistService:
    def __init__(self, db: Session, *, now: datetime | None = None) -> None:
        self.db = db
        self.applications = ApplicationRepository(db)
        self.checklists = ChecklistRepository(db)
        self.visits = SiteVisitRepository(db)
        self.audit = AuditRepository(db)
        self.users = UserRepository(db)
        self._now = now

    def now(self) -> datetime:
        return self._now or datetime.now(UTC)

    # Reads ---------------------------------------------------------------------------------------

    def get(self, user: User, application_id: uuid.UUID, *, visit_no: int | None = None) -> ChecklistOut:
        """The current visit's checklist, or an earlier visit's with `visit_no`. 404 until created."""
        app = self.applications.get_for(user, application_id)
        row = (
            self.checklists.get(app.id, visit_no)
            if visit_no is not None
            else self.checklists.current_for(app.id)
        )
        if row is None:
            raise NotFound("No checklist exists for this visit yet.")
        return self._out(row)

    def summary(self, app: Application) -> ChecklistSummaryOut | None:
        row = self.checklists.current_for(app.id)
        if row is None:
            return None
        items = self.checklists.items_for(row.id)
        return ChecklistSummaryOut(
            visit_no=row.visit_no,
            status=row.status.value,
            version=row.version,
            counts=counts_for(items),
            updated_at=row.updated_at,
            submitted_at=row.submitted_at,
        )

    def facts(self, app: Application) -> ChecklistFacts:
        """The guard facts for the current visit's checklist: `complete` opens the automatic hop after
        submit; the clarification counts drive the post-site edges (US-063 to US-066)."""
        row = self.checklists.current_for(app.id)
        if row is None or row.visit_no != self._current_visit_no(app):
            return NO_CHECKLIST
        items = self.checklists.items_for(row.id)
        open_items = sum(1 for i in items if i.clarification_status == ClarificationStatus.OPEN)
        answered = sum(1 for i in items if i.clarification_status == ClarificationStatus.ANSWERED)
        return ChecklistFacts(
            started=True,
            complete=row.status == ChecklistStatus.SUBMITTED,
            open_clarifications=open_items,
            answered_clarifications=answered,
            all_open_answered=open_items == 0 and answered > 0,
        )

    def started(self, app: Application) -> bool:
        return self.facts(app).started

    # Officer actions -----------------------------------------------------------------------------

    def create_or_get(self, officer: User, application_id: uuid.UUID) -> tuple[Checklist, bool]:
        """The current visit's draft: created on first open (True), returned afterwards (False).
        Under the application row lock so two tabs cannot create two."""
        app = self.applications.get_for(officer, application_id, for_update=True)
        if app.status not in SITE_VISIT_STATES:
            raise Conflict("The checklist opens once a site visit is scheduled.")
        visit_no = self._current_visit_no(app)
        existing = self.checklists.get(app.id, visit_no)
        if existing is not None:
            return existing, False
        row = Checklist(
            application_id=app.id,
            visit_no=visit_no,
            schema_version=CHECKLIST_VERSION,
            status=ChecklistStatus.DRAFT,
            version=1,
            created_by_id=officer.id,
            updated_at=self.now(),
        )
        self.checklists.add(row)
        self.db.flush()
        for key in ITEM_KEYS:
            self.checklists.add(
                ChecklistItem(
                    checklist_id=row.id,
                    item_key=key,
                    position=POSITION[key],
                    result=ChecklistResult.NOT_ASSESSED,
                    needs_clarification=False,
                    clarification_status=ClarificationStatus.NONE,
                )
            )
        self.audit.record(
            application_id=app.id,
            actor_id=officer.id,
            event_type="checklist.created",
            payload={"visit_no": visit_no, "schema_version": CHECKLIST_VERSION, "items": len(ITEM_KEYS)},
        )
        self.db.commit()
        return row, True

    def save(self, officer: User, application_id: uuid.UUID, body: ChecklistSaveIn) -> ChecklistOut:
        """Draft save (US-060; replay and merge in US-061): the whole item list, checked against
        the template, under the row lock and the optimistic version."""
        errors = self._validate_items(body.items)
        if errors:
            raise ValidationFailed("Some items need attention.", details={"fields": errors})
        app = self.applications.get_for(officer, application_id, for_update=True)
        row = self.checklists.current_for(app.id)
        if row is None:
            raise NotFound("No checklist exists for this visit yet.")
        if row.status == ChecklistStatus.SUBMITTED:
            raise Conflict(SUBMITTED_MESSAGE)
        if body.save_id and row.last_save_id == body.save_id:
            # The response was lost on the way back; the save itself landed. Answer with the state.
            return self._out(row)
        if row.version != body.version:
            raise VersionConflict(
                "This checklist changed since you opened it.",
                details={"current": self._out(row).model_dump(mode="json")},
            )
        items = {i.item_key: i for i in self.checklists.items_for(row.id)}
        for entry in body.items:
            item = items[entry.key]
            item.result = ChecklistResult(entry.result)
            item.comment = (entry.comment or "").strip() or None
            item.needs_clarification = entry.needs_clarification
        row.version += 1
        row.last_save_id = body.save_id
        row.updated_at = self.now()
        self.db.commit()
        return self._out(row)

    def submit(self, officer: User, application_id: uuid.UUID) -> ChecklistOut:
        """Freeze the findings and move the case (US-063, FR-040): every item assessed, every
        unsatisfactory or flagged item commented (422 listing the keys); from Site Visit Scheduled the
        officer's hop to Site Visit Done is recorded first, then the system hop to Awaiting Post-Site
        Clarification; round-1 requests are created and released for the flagged items; one
        notification tells the operator how many items need them."""
        from app.services.workflow import WorkflowService  # noqa: PLC0415 - the services call each other

        app = self.applications.get_for(officer, application_id, for_update=True)
        if app.status not in SITE_VISIT_STATES:
            raise Conflict("The checklist can be submitted while the case is in a site-visit state.")
        row = self.checklists.get(app.id, self._current_visit_no(app))
        if row is None:
            raise NotFound("No checklist exists for this visit yet.")
        if row.status == ChecklistStatus.SUBMITTED:
            raise Conflict("This checklist was already submitted.")
        items = self.checklists.items_for(row.id)
        problems: dict[str, str] = {}
        for i in items:
            if i.result == ChecklistResult.NOT_ASSESSED:
                problems[i.item_key] = "Assess this item."
            elif (i.result == ChecklistResult.UNSATISFACTORY or i.needs_clarification) and not (
                i.comment or ""
            ).strip():
                problems[i.item_key] = "Add a comment: the operator will read it."
        if problems:
            word = "item needs" if len(problems) == 1 else "items need"
            raise ValidationFailed(
                f"{len(problems)} {word} attention before submit.",
                details={"fields": problems, "items": list(problems)},
            )
        now = self.now()
        workflow = WorkflowService(self.db)
        if app.status == ApplicationStatus.SITE_VISIT_SCHEDULED:
            # The officer's own hop first, audited as such; the operator hears once, below.
            workflow.apply(app, ApplicationStatus.SITE_VISIT_DONE, officer, note=None, notify_operator=False)
        row.status = ChecklistStatus.SUBMITTED
        row.submitted_by_id = officer.id
        row.submitted_at = now
        row.updated_at = now
        row.version += 1
        flagged = [i for i in items if i.needs_clarification]
        for i in flagged:
            self.checklists.add(
                ClarificationRequest(
                    item_id=i.id,
                    round_no=1,
                    author_id=officer.id,
                    message=(i.comment or "").strip(),
                    released_at=now,
                    created_at=now,
                )
            )
            i.clarification_status = ClarificationStatus.OPEN
        counts = counts_for(items)
        self.audit.record(
            application_id=app.id,
            actor_id=officer.id,
            event_type="checklist.submitted",
            payload={
                "visit_no": row.visit_no,
                "total": counts.total,
                "satisfactory": counts.total - counts.unsatisfactory - counts.not_applicable,
                "unsatisfactory": counts.unsatisfactory,
                "not_applicable": counts.not_applicable,
                "flagged_keys": [i.item_key for i in flagged],
            },
        )
        self.db.flush()
        n = len(flagged)
        body = (
            f"The licensing officer completed the site visit and needs more information on {n} "
            f"{'item' if n == 1 else 'items'}. Open the application to answer."
            if n
            else (
                "The site visit is recorded; nothing is needed from you while the officer "
                "finalises the assessment."
            )
        )

        workflow.apply(
            app,
            ApplicationStatus.AWAITING_POST_SITE_CLARIFICATION,
            officer,
            note=None,
            actor=Actor.SYSTEM,
            operator_body=body,
        )
        self.db.commit()
        workflow.notifications.flush_sent()
        return self._out(row)

    # Helpers -------------------------------------------------------------------------------------

    def _current_visit_no(self, app: Application) -> int:
        visit = self.visits.current_for(app.id)
        if visit is not None:
            return visit.visit_no
        # A case scheduled through the API before a date was proposed: the next number on record.
        latest = self.checklists.current_for(app.id)
        return (
            (latest.visit_no + 1)
            if latest and latest.status == ChecklistStatus.SUBMITTED
            else (latest.visit_no if latest else 1)
        )

    @staticmethod
    def _validate_items(entries: list[ChecklistItemIn]) -> dict[str, str]:
        errors: dict[str, str] = {}
        seen: set[str] = set()
        for e in entries:
            if e.key not in ITEM_BY_KEY:
                errors[e.key] = "This item is not on the checklist."
                continue
            if e.key in seen:
                errors[e.key] = "This item appears twice."
                continue
            seen.add(e.key)
            try:
                ChecklistResult(e.result)
            except ValueError:
                errors[e.key] = "Choose Satisfactory, Unsatisfactory or Not applicable."
            if e.comment is not None and len(e.comment) > MAX_COMMENT:
                errors[e.key] = f"Keep the comment under {MAX_COMMENT} characters."
        missing = [k for k in ITEM_KEYS if k not in seen]
        if missing and not errors:
            errors["items"] = f"Every item must be sent: {len(missing)} missing."
        return errors

    def _out(self, row: Checklist) -> ChecklistOut:
        items = self.checklists.items_for(row.id)
        counts = counts_for(items)
        creator = self.users.get(row.created_by_id)
        submitter = self.users.get(row.submitted_by_id) if row.submitted_by_id else None
        return ChecklistOut(
            id=row.id,
            application_id=row.application_id,
            visit_no=row.visit_no,
            schema_version=row.schema_version,
            status=row.status.value,
            version=row.version,
            created_by=creator.full_name if creator else "",
            created_at=row.created_at,
            updated_at=row.updated_at,
            submitted_by=submitter.full_name if submitter else None,
            submitted_at=row.submitted_at,
            counts=counts,
            remaining=remaining_sentence(counts),
            items=[
                ChecklistItemOut(
                    id=i.id,
                    key=i.item_key,
                    section=ITEM_BY_KEY[i.item_key].section,
                    title=ITEM_BY_KEY[i.item_key].title,
                    guidance=ITEM_BY_KEY[i.item_key].guidance,
                    position=i.position,
                    result=i.result.value,
                    comment=i.comment,
                    needs_clarification=i.needs_clarification,
                    clarification_status=i.clarification_status.value,
                )
                for i in items
            ],
        )
