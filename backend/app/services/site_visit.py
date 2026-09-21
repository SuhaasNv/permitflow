"""The site visit appointment (US-084, FR-043): the officer proposes a date and slot, the operator accepts
or proposes another with a reason, the officer decides, either side can reschedule before the date, the
officer can confirm after three working days of silence, and the visit is marked done only once confirmed.

No new application status: the appointment lives inside `site_visit_scheduled`. Every mutation locks the
application row, writes its audit row and its notification in the same transaction (ADR-008)."""

import uuid
from datetime import UTC, date, datetime

from sqlalchemy.orm import Session

from app.core.errors import Conflict, NotFound, ValidationFailed
from app.domain.enums import (
    ApplicationStatus,
    NotificationKind,
    Role,
    SiteVisitProposalOutcome,
    SiteVisitSlot,
    SiteVisitStatus,
)
from app.domain.site_visit import (
    PAST_DATE_REASON,
    ROUND_LIMIT_REASON,
    date_problem,
    earliest_date,
    format_visit,
    reply_deadline,
    rounds_left,
    short_visit,
    today_in_singapore,
)
from app.models import Application, SiteVisit, SiteVisitProposal, User
from app.repositories.applications import ApplicationRepository
from app.repositories.audit import AuditRepository
from app.repositories.site_visits import SiteVisitRepository
from app.repositories.users import UserRepository
from app.schemas.site_visit import SiteVisitOperatorView, SiteVisitOut, SiteVisitProposalOut
from app.services.notifications import NotificationService

MAX_REASON = 500
MAX_NOTE = 500

OPERATOR_WORDS: dict[SiteVisitStatus, str] = {
    SiteVisitStatus.PROPOSED: "Waiting for your reply",
    SiteVisitStatus.COUNTER_PROPOSED: "Waiting for the officer",
    SiteVisitStatus.CONFIRMED: "Confirmed",
    SiteVisitStatus.DONE: "Done",
}
OPERATOR_LIMIT_REASON = "No more dates can be proposed for this visit. You can still accept this one."
OFFICER_LIMIT_REASON = (
    "No more dates can be proposed for this visit: accept the operator's date or keep the one on the table."
)
OFFICER_WORDS: dict[SiteVisitStatus, str] = {
    SiteVisitStatus.PROPOSED: "Waiting for the operator",
    SiteVisitStatus.COUNTER_PROPOSED: "Waiting for you",
    SiteVisitStatus.CONFIRMED: "Confirmed",
    SiteVisitStatus.DONE: "Done",
}


class SiteVisitService:
    def __init__(self, db: Session, *, now: datetime | None = None) -> None:
        self.db = db
        self.applications = ApplicationRepository(db)
        self.visits = SiteVisitRepository(db)
        self.audit = AuditRepository(db)
        self.users = UserRepository(db)
        self.notifications = NotificationService(db)
        # Injected by tests that walk the calendar (the reply deadline, the working-day rules).
        self._now = now

    # Reads ---------------------------------------------------------------------------------------

    def now(self) -> datetime:
        return self._now or datetime.now(UTC)

    def today(self) -> date:
        return today_in_singapore(self.now())

    def officer_view(self, app: Application) -> SiteVisitOut | None:
        visit = self.visits.current_for(app.id)
        if visit is None:
            return None
        proposals = self.visits.proposals_for(visit.id)
        last_officer = next((p for p in reversed(proposals) if p.author_role == Role.OFFICER.value), None)
        deadline = reply_deadline(last_officer.created_at, visit.date) if last_officer else None
        today = self.today()
        expired = visit.status == SiteVisitStatus.PROPOSED and visit.date <= today
        can_confirm = (
            visit.status == SiteVisitStatus.PROPOSED
            and deadline is not None
            and today >= deadline
            and not expired
        )
        left = rounds_left(len(proposals))
        # A confirmed visit still ahead can be moved; so can a proposal the operator let expire (its date
        # arrived unanswered), which is otherwise a dead end (review finding, 21 Sep).
        reschedulable = (
            (visit.status == SiteVisitStatus.CONFIRMED and visit.date > today) or expired
        ) and left > 0
        return SiteVisitOut(
            visit_no=visit.visit_no,
            status=visit.status.value,
            status_label=OFFICER_WORDS[visit.status],
            date=visit.date,
            slot=visit.slot.value,
            when=format_visit(visit.date, visit.slot),
            note=visit.note,
            reply_deadline=deadline,
            can_confirm_without_reply=can_confirm,
            confirm_without_reply_reason=(
                None
                if can_confirm
                else (
                    PAST_DATE_REASON
                    if expired
                    else (
                        f"Available from {deadline.strftime('%-d %b %Y')} if the operator has not replied."
                        if visit.status == SiteVisitStatus.PROPOSED and deadline
                        else "Only for a proposal the operator has left unanswered."
                    )
                )
            ),
            original=self._original(visit, proposals),
            counter=self._pending_counter(visit, proposals),
            can_reschedule=reschedulable,
            rounds_left=left,
            round_limit_reason=OFFICER_LIMIT_REASON if left == 0 else None,
            rounds=[self._proposal_out(p) for p in proposals],
        )

    def operator_view(self, app: Application) -> SiteVisitOperatorView | None:
        visit = self.visits.current_for(app.id)
        if visit is None:
            return None
        proposals = self.visits.proposals_for(visit.id)
        last_officer = next((p for p in reversed(proposals) if p.author_role == Role.OFFICER.value), None)
        deadline = reply_deadline(last_officer.created_at, visit.date) if last_officer else None
        left = rounds_left(len(proposals))
        reschedulable = visit.status == SiteVisitStatus.CONFIRMED and visit.date > self.today() and left > 0
        return SiteVisitOperatorView(
            visit_no=visit.visit_no,
            status=visit.status.value,
            status_label=OPERATOR_WORDS[visit.status],
            date=visit.date,
            slot=visit.slot.value,
            when=format_visit(visit.date, visit.slot),
            note=visit.note,
            reply_by=deadline if visit.status == SiteVisitStatus.PROPOSED else None,
            can_accept=visit.status == SiteVisitStatus.PROPOSED and visit.date > self.today(),
            can_counter=visit.status == SiteVisitStatus.PROPOSED and left > 0,
            can_reschedule=reschedulable,
            earliest_date=earliest_date(self.today(), by_operator=True),
            rounds_left=left,
            round_limit_reason=OPERATOR_LIMIT_REASON if left == 0 else None,
            # The officer's name stays inside the office (T3): operators see the role, never the person.
            rounds=[self._proposal_out(p, mask_officer=True) for p in proposals],
        )

    def awaits_operator(self, app_ids: list[uuid.UUID]) -> set[uuid.UUID]:
        """Applications whose current visit waits on the operator (the dashboard's Needs your response)."""
        return {
            aid
            for aid, v in self.visits.current_for_many(app_ids).items()
            if v.status == SiteVisitStatus.PROPOSED
        }

    def statuses(self, app_ids: list[uuid.UUID]) -> dict[uuid.UUID, SiteVisitStatus]:
        return {aid: v.status for aid, v in self.visits.current_for_many(app_ids).items()}

    # Officer actions -----------------------------------------------------------------------------

    def propose(
        self,
        officer: User,
        application_id: uuid.UUID,
        *,
        visit_date: date,
        slot: str,
        note: str | None,
        expected_version: int,
    ) -> SiteVisit:
        """The officer's first proposal for the current visit. From Under Review the case moves to Site
        Visit Scheduled in the same transaction (the guard of that edge still applies); from Site Visit
        Scheduled without a visit (a case scheduled before US-084, or a second visit) it records one."""
        from app.services.workflow import WorkflowService  # noqa: PLC0415 - the two services call each other

        slot_value = self._slot(slot)
        note = self._text(note, MAX_NOTE, "note", required=False)
        problem = date_problem(visit_date, self.today(), by_operator=False)
        if problem:
            raise ValidationFailed("Some fields need attention.", details={"fields": {"date": problem}})
        app = self.applications.get_for(officer, application_id, for_update=True)
        if app.version != expected_version:
            raise Conflict("This application changed since you opened it. Reload to see the latest.")
        if app.status == ApplicationStatus.UNDER_REVIEW:
            WorkflowService(self.db).apply(app, ApplicationStatus.SITE_VISIT_SCHEDULED, officer, note=None)
        if app.status != ApplicationStatus.SITE_VISIT_SCHEDULED:
            raise Conflict(
                "A site visit can be proposed while the case is Under Review or Site Visit Scheduled."
            )
        current = self.visits.current_for(app.id)
        if current is not None and current.status != SiteVisitStatus.DONE:
            raise Conflict("A visit is already proposed for this application; decide or reschedule it.")
        visit_no = (current.visit_no + 1) if current else 1
        visit = SiteVisit(
            application_id=app.id,
            visit_no=visit_no,
            status=SiteVisitStatus.PROPOSED,
            date=visit_date,
            slot=slot_value,
            note=note,
            proposed_by_id=officer.id,
            updated_at=self.now(),
        )
        self.visits.add(visit)
        self.db.flush()
        self._add_proposal(visit, officer, Role.OFFICER, 1, visit_date, slot_value, None)
        self._audit(app, officer, "site_visit.proposed", visit, {"round": 1, "note": bool(note)})
        self._notify_operator(
            app,
            "Site visit proposed",
            f"The licensing officer proposed a site visit on {short_visit(visit_date, slot_value)}. "
            "Accept the date or propose another one.",
        )
        self.db.commit()
        self.notifications.flush_sent()
        return visit

    def decide(
        self,
        officer: User,
        application_id: uuid.UUID,
        *,
        action: str,
        visit_date: date | None,
        slot: str | None,
        note: str | None,
    ) -> SiteVisit:
        """On a counter-proposal: accept the operator's date, keep the original, or propose a third."""
        if action not in ("accept_operator", "keep_original", "propose"):
            raise ValidationFailed(
                "Some fields need attention.", details={"fields": {"action": "Choose what to do."}}
            )
        app = self.applications.get_for(officer, application_id, for_update=True)
        visit = self._current(
            app, SiteVisitStatus.COUNTER_PROPOSED, "The operator has not proposed another date."
        )
        proposals = self.visits.proposals_for(visit.id)
        counter = proposals[-1]
        # The date on the table is the visit's own (proposed by the officer, or the one confirmed before
        # the operator asked to move it). Only an officer proposal still pending is settled here: after a
        # reschedule of a confirmed visit the earlier rounds keep the outcome they already have.
        open_officer = next(
            (
                p
                for p in reversed(proposals)
                if p.author_role == Role.OFFICER.value and p.outcome == SiteVisitProposalOutcome.PENDING
            ),
            None,
        )
        now = self.now()
        if action == "accept_operator":
            self._refuse_past(counter.date)
            self._settle(counter, SiteVisitProposalOutcome.ACCEPTED, now)
            if open_officer:
                self._settle(open_officer, SiteVisitProposalOutcome.DECLINED, now)
            self._confirm(visit, officer, counter.date, counter.slot, now)
            self._audit(app, officer, "site_visit.confirmed", visit, {"how": "accepted_operator_date"})
            self._notify_operator(
                app,
                "Site visit confirmed",
                f"The licensing officer accepted your date: {format_visit(visit.date, visit.slot)}.",
            )
        elif action == "keep_original":
            self._refuse_past(visit.date)
            self._settle(counter, SiteVisitProposalOutcome.DECLINED, now)
            if open_officer:
                self._settle(open_officer, SiteVisitProposalOutcome.KEPT, now)
            self._confirm(visit, officer, visit.date, visit.slot, now)
            self._audit(app, officer, "site_visit.confirmed", visit, {"how": "kept_original_date"})
            self._notify_operator(
                app,
                "Site visit confirmed",
                f"The licensing officer kept the original date: {format_visit(visit.date, visit.slot)}.",
            )
        else:
            if visit_date is None:
                raise ValidationFailed(
                    "Some fields need attention.", details={"fields": {"date": "Choose a date."}}
                )
            slot_value = self._slot(slot or "")
            note = self._text(note, MAX_NOTE, "note", required=False)
            problem = date_problem(visit_date, self.today(), by_operator=False)
            if problem:
                raise ValidationFailed("Some fields need attention.", details={"fields": {"date": problem}})
            self._check_rounds(proposals)
            self._settle(counter, SiteVisitProposalOutcome.DECLINED, now)
            if open_officer:
                self._settle(open_officer, SiteVisitProposalOutcome.SUPERSEDED, now)
            visit.status = SiteVisitStatus.PROPOSED
            visit.date, visit.slot, visit.note = visit_date, slot_value, note
            visit.proposed_by_id = officer.id
            visit.updated_at = now
            round_no = self._add_proposal(
                visit, officer, Role.OFFICER, len(proposals) + 1, visit_date, slot_value, note
            )
            self._audit(app, officer, "site_visit.proposed", visit, {"round": round_no, "note": bool(note)})
            self._notify_operator(
                app,
                "Site visit: another date proposed",
                f"The licensing officer proposed {short_visit(visit_date, slot_value)} instead. "
                "Accept the date or propose another one.",
            )
        self.db.commit()
        self.notifications.flush_sent()
        return visit

    def confirm_without_reply(self, officer: User, application_id: uuid.UUID) -> SiteVisit:
        app = self.applications.get_for(officer, application_id, for_update=True)
        visit = self._current(app, SiteVisitStatus.PROPOSED, "Only a proposal the operator left unanswered.")
        proposals = self.visits.proposals_for(visit.id)
        last = proposals[-1]
        deadline = reply_deadline(last.created_at, visit.date)
        if self.today() < deadline:
            raise Conflict(f"The operator has until {deadline.strftime('%-d %b %Y')} to reply.")
        self._refuse_past(visit.date)
        now = self.now()
        self._settle(last, SiteVisitProposalOutcome.ACCEPTED, now)
        self._confirm(visit, officer, visit.date, visit.slot, now)
        self._audit(app, officer, "site_visit.confirmed", visit, {"how": "confirmed_without_reply"})
        self._notify_operator(
            app,
            "Site visit confirmed",
            f"No reply was received, so the visit is confirmed for {format_visit(visit.date, visit.slot)}.",
        )
        self.db.commit()
        self.notifications.flush_sent()
        return visit

    def reschedule(
        self,
        user: User,
        application_id: uuid.UUID,
        *,
        visit_date: date,
        slot: str,
        reason: str | None,
    ) -> SiteVisit:
        """Either side asks for a different date before a confirmed visit happens (reason required).
        The officer's request becomes a proposal the operator answers; the operator's a counter-proposal
        the officer decides."""
        slot_value = self._slot(slot)
        reason_text = self._text(reason, MAX_REASON, "reason", required=True)
        by_operator = user.role == Role.OPERATOR
        problem = date_problem(visit_date, self.today(), by_operator=by_operator)
        if problem:
            raise ValidationFailed("Some fields need attention.", details={"fields": {"date": problem}})
        app = self.applications.get_for(user, application_id, for_update=True)
        if app.status != ApplicationStatus.SITE_VISIT_SCHEDULED:
            raise Conflict("The site visit can be arranged only while the appointment is still open.")
        visit = self.visits.current_for(app.id)
        if visit is None:
            raise NotFound("No site visit has been proposed.")
        expired = visit.status == SiteVisitStatus.PROPOSED and visit.date <= self.today()
        if visit.status == SiteVisitStatus.CONFIRMED:
            if visit.date <= self.today():
                raise Conflict("The visit date has arrived; it can no longer be rescheduled.")
        elif not expired:
            raise Conflict("Only a confirmed visit, or a proposal whose date has passed, can be rescheduled.")
        proposals = self.visits.proposals_for(visit.id)
        self._check_rounds(proposals)
        now = self.now()
        if expired:
            # The unanswered proposal lapsed with its date: settled as declined, and the round moves on.
            for p in proposals:
                if p.outcome == SiteVisitProposalOutcome.PENDING:
                    self._settle(p, SiteVisitProposalOutcome.DECLINED, now)
        role = Role.OPERATOR if by_operator else Role.OFFICER
        visit.status = SiteVisitStatus.COUNTER_PROPOSED if by_operator else SiteVisitStatus.PROPOSED
        visit.confirmed_at, visit.confirmed_by_id = None, None
        visit.updated_at = now
        if by_operator:
            # The confirmed date stays on the visit until the officer decides; the counter carries the ask.
            round_no = self._add_proposal(
                visit, user, role, len(proposals) + 1, visit_date, slot_value, reason_text
            )
        else:
            visit.date, visit.slot = visit_date, slot_value
            visit.proposed_by_id = user.id
            round_no = self._add_proposal(
                visit, user, role, len(proposals) + 1, visit_date, slot_value, reason_text
            )
        self._audit(app, user, "site_visit.rescheduled", visit, {"round": round_no, "by": role.value})
        if by_operator:
            self._notify_officers(
                app,
                "Site visit: operator asks to reschedule",
                f"{user.full_name} asks to move the visit to {short_visit(visit_date, slot_value)}: "
                f"{reason_text}",
            )
        else:
            self._notify_operator(
                app,
                "Site visit: new date proposed",
                f"The licensing officer needs to move the visit to {short_visit(visit_date, slot_value)}: "
                f"{reason_text} Accept the date or propose another one.",
            )
        self.db.commit()
        self.notifications.flush_sent()
        return visit

    # Operator actions ----------------------------------------------------------------------------

    def accept(self, operator: User, application_id: uuid.UUID) -> SiteVisit:
        app = self.applications.get_for(operator, application_id, for_update=True)
        visit = self._current(app, SiteVisitStatus.PROPOSED, "There is no proposal waiting for your reply.")
        self._refuse_past(visit.date)
        proposals = self.visits.proposals_for(visit.id)
        now = self.now()
        self._settle(proposals[-1], SiteVisitProposalOutcome.ACCEPTED, now)
        self._confirm(visit, operator, visit.date, visit.slot, now)
        self._audit(app, operator, "site_visit.confirmed", visit, {"how": "accepted_by_operator"})
        self._notify_officers(
            app,
            "Site visit confirmed",
            f"{operator.full_name} accepted the visit on {format_visit(visit.date, visit.slot)}.",
        )
        self.db.commit()
        self.notifications.flush_sent()
        return visit

    def counter(
        self, operator: User, application_id: uuid.UUID, *, visit_date: date, slot: str, reason: str | None
    ) -> SiteVisit:
        slot_value = self._slot(slot)
        reason_text = self._text(reason, MAX_REASON, "reason", required=True)
        problem = date_problem(visit_date, self.today(), by_operator=True)
        if problem:
            raise ValidationFailed("Some fields need attention.", details={"fields": {"date": problem}})
        app = self.applications.get_for(operator, application_id, for_update=True)
        visit = self._current(app, SiteVisitStatus.PROPOSED, "There is no proposal waiting for your reply.")
        proposals = self.visits.proposals_for(visit.id)
        self._check_rounds(proposals)
        now = self.now()
        visit.status = SiteVisitStatus.COUNTER_PROPOSED
        visit.updated_at = now
        round_no = self._add_proposal(
            visit, operator, Role.OPERATOR, len(proposals) + 1, visit_date, slot_value, reason_text
        )
        self._audit(app, operator, "site_visit.counter_proposed", visit, {"round": round_no})
        self._notify_officers(
            app,
            "Site visit: operator proposes another date",
            f"{operator.full_name} proposes {short_visit(visit_date, slot_value)}: {reason_text}",
        )
        self.db.commit()
        self.notifications.flush_sent()
        return visit

    # Workflow hook -------------------------------------------------------------------------------

    def mark_done(self, app: Application, now: datetime) -> None:
        """Called by the workflow service inside the `site_visit_done` transaction (no commit here)."""
        visit = self.visits.current_for(app.id)
        if visit is not None and visit.status == SiteVisitStatus.CONFIRMED:
            visit.status = SiteVisitStatus.DONE
            visit.done_at = now
            visit.updated_at = now

    def visit_confirmed(self, app: Application) -> bool:
        visit = self.visits.current_for(app.id)
        return visit is not None and visit.status == SiteVisitStatus.CONFIRMED

    # Helpers -------------------------------------------------------------------------------------

    def _current(self, app: Application, expected: SiteVisitStatus, message: str) -> SiteVisit:
        if app.status != ApplicationStatus.SITE_VISIT_SCHEDULED:
            # Role-neutral: the operator's label for this status differs from the officer's (review, 21 Sep).
            raise Conflict("The site visit can be arranged only while the appointment is still open.")
        visit = self.visits.current_for(app.id)
        if visit is None:
            raise NotFound("No site visit has been proposed.")
        if visit.status != expected:
            raise Conflict(message)
        return visit

    def _refuse_past(self, visit_date: date) -> None:
        """A date that has arrived is never confirmed (review finding, 21 Sep): the other side proposes."""
        if visit_date <= self.today():
            raise Conflict(PAST_DATE_REASON)

    @staticmethod
    def _check_rounds(proposals: list[SiteVisitProposal]) -> None:
        if rounds_left(len(proposals)) == 0:
            raise Conflict(ROUND_LIMIT_REASON)

    @staticmethod
    def _slot(slot: str) -> SiteVisitSlot:
        try:
            return SiteVisitSlot(slot)
        except ValueError:
            raise ValidationFailed(
                "Some fields need attention.", details={"fields": {"slot": "Choose morning or afternoon."}}
            ) from None

    @staticmethod
    def _text(value: str | None, limit: int, field: str, *, required: bool) -> str | None:
        text = (value or "").strip()
        if not text:
            if required:
                raise ValidationFailed(
                    "Some fields need attention.",
                    details={"fields": {field: "Say why, in a sentence the other side will read."}},
                )
            return None
        if len(text) > limit:
            raise ValidationFailed(
                "Some fields need attention.",
                details={"fields": {field: f"Keep it under {limit} characters."}},
            )
        return text

    def _add_proposal(
        self,
        visit: SiteVisit,
        author: User,
        role: Role,
        round_no: int,
        visit_date: date,
        slot: SiteVisitSlot,
        reason: str | None,
    ) -> int:
        self.visits.add(
            SiteVisitProposal(
                site_visit_id=visit.id,
                round_no=round_no,
                author_id=author.id,
                author_role=role.value,
                date=visit_date,
                slot=slot,
                reason=reason,
                outcome=SiteVisitProposalOutcome.PENDING,
                created_at=self.now(),
            )
        )
        return round_no

    @staticmethod
    def _settle(proposal: SiteVisitProposal, outcome: SiteVisitProposalOutcome, now: datetime) -> None:
        proposal.outcome = outcome
        proposal.decided_at = now

    @staticmethod
    def _confirm(visit: SiteVisit, by: User, visit_date: date, slot: SiteVisitSlot, now: datetime) -> None:
        visit.status = SiteVisitStatus.CONFIRMED
        visit.date, visit.slot = visit_date, slot
        visit.confirmed_at, visit.confirmed_by_id = now, by.id
        visit.updated_at = now

    def _audit(
        self, app: Application, actor: User, event_type: str, visit: SiteVisit, extra: dict[str, object]
    ) -> None:
        self.audit.record(
            application_id=app.id,
            actor_id=actor.id,
            event_type=event_type,
            payload={
                "visit_no": visit.visit_no,
                "date": visit.date.isoformat(),
                "slot": visit.slot.value,
                "status": visit.status.value,
                **extra,
            },
        )

    def _notify_operator(self, app: Application, title: str, body: str) -> None:
        self.notifications.notify_user(
            app.operator_id, app, NotificationKind.STATUS_CHANGED, f"{app.reference_no}: {title}", body
        )

    def _notify_officers(self, app: Application, title: str, body: str) -> None:
        self.notifications.notify_officers(
            app, NotificationKind.RESUBMITTED, f"{app.reference_no}: {title}", body
        )

    def _original(self, visit: SiteVisit, proposals: list[SiteVisitProposal]) -> SiteVisitProposalOut | None:
        """The round that put the date on the table: the last one matching the visit's date and slot."""
        match = next((p for p in reversed(proposals) if p.date == visit.date and p.slot == visit.slot), None)
        return self._proposal_out(match) if match else None

    def _pending_counter(
        self, visit: SiteVisit, proposals: list[SiteVisitProposal]
    ) -> SiteVisitProposalOut | None:
        if visit.status != SiteVisitStatus.COUNTER_PROPOSED or not proposals:
            return None
        return self._proposal_out(proposals[-1])

    def _proposal_out(self, p: SiteVisitProposal, *, mask_officer: bool = False) -> SiteVisitProposalOut:
        author = self.users.get(p.author_id)
        officer_round = p.author_role == Role.OFFICER.value
        return SiteVisitProposalOut(
            round=p.round_no,
            author_role=p.author_role,
            author_name=(
                "Licensing officer"
                if officer_round and mask_officer
                else (author.full_name if author else "")
            ),
            date=p.date,
            slot=p.slot.value,
            when=format_visit(p.date, p.slot),
            reason=p.reason,
            outcome=p.outcome.value,
            created_at=p.created_at,
            decided_at=p.decided_at,
        )
