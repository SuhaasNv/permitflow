"""The site visit appointment (US-084) as each role sees it. The operator view carries no application
status code and no officer-only wording (the appointment's own state names, `proposed`, `counter_proposed`,
`confirmed`, `done`, are allowed: threat model T24); the officer view carries the decision controls."""

import datetime as dt

from pydantic import BaseModel, Field


class SiteVisitProposalOut(BaseModel):
    round: int
    author_role: str
    author_name: str
    date: dt.date
    slot: str
    when: str
    reason: str | None
    outcome: str
    created_at: dt.datetime
    decided_at: dt.datetime | None


class SiteVisitOut(BaseModel):
    """Officer view: the current appointment, the operator's counter when one waits, the rounds."""

    visit_no: int
    status: str
    status_label: str
    date: dt.date
    slot: str
    when: str
    note: str | None
    reply_deadline: dt.date | None
    can_confirm_without_reply: bool
    confirm_without_reply_reason: str | None
    original: SiteVisitProposalOut | None
    counter: SiteVisitProposalOut | None
    can_reschedule: bool
    # Proposals both sides may still add to this visit; at zero only accept or keep remain.
    rounds_left: int
    round_limit_reason: str | None
    rounds: list[SiteVisitProposalOut]
    # The confirmed date still stands: confirmed, or the operator asked to move it and the officer has not
    # decided yet (UC3-0 4a). The checklist stays open on such a visit (UAT run 5, F8).
    date_stands: bool = False
    # Mark site visit done and the checklist submit wait for the visit day (Singapore date; F12).
    visit_day_reached: bool = False
    # False for an earlier visit shown as history: nothing on it can change.
    is_current: bool = True


class SiteVisitOperatorView(BaseModel):
    """Operator view: the date on the table, what they can do, and every round in their own words."""

    visit_no: int
    status: str
    status_label: str
    date: dt.date
    slot: str
    when: str
    note: str | None
    reply_by: dt.date | None
    can_accept: bool
    can_counter: bool
    can_reschedule: bool
    earliest_date: dt.date
    rounds_left: int
    round_limit_reason: str | None
    rounds: list[SiteVisitProposalOut]
    date_stands: bool = False
    is_current: bool = True


class SiteVisitProposeIn(BaseModel):
    date: dt.date
    slot: str
    note: str | None = Field(default=None, max_length=500)
    # The transition to Site Visit Scheduled happens in the same request; the version guards it.
    expected_version: int


class SiteVisitDecideIn(BaseModel):
    action: str  # accept_operator | keep_original | propose
    date: dt.date | None = None
    slot: str | None = None
    note: str | None = Field(default=None, max_length=500)


class SiteVisitRescheduleIn(BaseModel):
    date: dt.date
    slot: str
    reason: str | None = Field(default=None, max_length=500)


class SiteVisitCounterIn(BaseModel):
    date: dt.date
    slot: str
    reason: str | None = Field(default=None, max_length=500)


__all__ = [
    "SiteVisitCounterIn",
    "SiteVisitDecideIn",
    "SiteVisitOperatorView",
    "SiteVisitOut",
    "SiteVisitProposalOut",
    "SiteVisitProposeIn",
    "SiteVisitRescheduleIn",
]
