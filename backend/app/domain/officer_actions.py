"""What an officer does next with an application, derived from its status (pure)."""

from dataclasses import dataclass

from app.domain.enums import ApplicationStatus as S


@dataclass(frozen=True)
class NextAction:
    label: str
    # True when the licensing office is expected to act; False when waiting on the operator or decided.
    officer_turn: bool


_ACTIONS: dict[S, NextAction] = {
    S.DRAFT: NextAction("Not submitted", False),
    S.APPLICATION_RECEIVED: NextAction("Start review", True),
    S.UNDER_REVIEW: NextAction("Continue review", True),
    S.PENDING_PRE_SITE_RESUBMISSION: NextAction("Waiting on operator", False),
    S.PRE_SITE_RESUBMITTED: NextAction("Review resubmission", True),
    S.SITE_VISIT_SCHEDULED: NextAction("Record site visit", True),
    S.SITE_VISIT_DONE: NextAction("Continue", True),
    S.AWAITING_POST_SITE_CLARIFICATION: NextAction("Continue", True),
    S.PENDING_POST_SITE_RESUBMISSION: NextAction("Waiting on operator", False),
    S.POST_SITE_CLARIFICATION_RESUBMITTED: NextAction("Review clarification", True),
    S.PENDING_APPROVAL: NextAction("Decide", True),
    S.APPROVED: NextAction("View", False),
    S.REJECTED: NextAction("View", False),
    S.WITHDRAWN: NextAction("View", False),
}


def next_action(status: S) -> NextAction:
    return _ACTIONS[status]


def is_decided(status: S) -> bool:
    return status in (S.APPROVED, S.REJECTED, S.WITHDRAWN)
