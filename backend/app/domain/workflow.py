"""Application state machine (ADR-003, STATE_MACHINE.md).

Pure: no database, no framework. The service layer builds a `TransitionContext` from the row it
has locked, and calls `transition()`. Every (from, to) pair not listed is invalid.
"""

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum

from app.domain.enums import ApplicationStatus as S
from app.domain.enums import Role


class Actor(StrEnum):
    OPERATOR = "operator"
    OFFICER = "officer"
    SYSTEM = "system"


@dataclass(frozen=True)
class TransitionContext:
    open_feedback_count: int = 0
    has_changes_to_flagged_targets: bool = False
    is_complete: bool = False
    has_note: bool = False
    # Use case 3 (v0.4.0, US-079): the checklist and the clarification items of the current visit.
    checklist_complete: bool = False  # every item assessed, every flagged or unsatisfactory item commented
    open_clarification_count: int = 0  # items waiting for the operator (or drafted, not yet sent)
    answered_clarification_count: int = 0  # items the operator answered that the officer has not decided
    all_open_items_answered: bool = False  # every open item carries a response in this round
    visit_confirmed: bool = False  # the site visit appointment is confirmed (US-084)


Guard = Callable[[TransitionContext], str | None]  # returns a failure reason or None


def _needs_complete(ctx: TransitionContext) -> str | None:
    return None if ctx.is_complete else "Complete every required section and document before submitting."


def _needs_open_feedback(ctx: TransitionContext) -> str | None:
    return None if ctx.open_feedback_count >= 1 else "At least one open feedback item is required."


def _needs_no_open_feedback(ctx: TransitionContext) -> str | None:
    if ctx.open_feedback_count == 0:
        return None
    return "Resolve or withdraw open feedback before scheduling a site visit."


def _needs_flagged_change(ctx: TransitionContext) -> str | None:
    return None if ctx.has_changes_to_flagged_targets else "No changes made to flagged items."


def _needs_note(ctx: TransitionContext) -> str | None:
    return None if ctx.has_note else "A note is required for this decision."


def _needs_visit_confirmed(ctx: TransitionContext) -> str | None:
    return None if ctx.visit_confirmed else "Confirm the visit date with the operator first."


def _needs_checklist_complete(ctx: TransitionContext) -> str | None:
    if ctx.checklist_complete:
        return None
    return "Assess every item and comment on each flagged or unsatisfactory item before submitting."


def _needs_open_clarification(ctx: TransitionContext) -> str | None:
    if ctx.open_clarification_count >= 1:
        return None
    return "At least one item must still need clarification."


def _needs_all_answered(ctx: TransitionContext) -> str | None:
    return None if ctx.all_open_items_answered else "Answer every item before sending your responses."


def _needs_nothing_open(ctx: TransitionContext) -> str | None:
    if ctx.open_clarification_count == 0 and ctx.answered_clarification_count == 0:
        return None
    return "Mark every clarification item clarified or withdraw it before routing to approval."


@dataclass(frozen=True)
class Transition:
    source: S
    target: S
    actor: Actor
    guard: Guard | None = None
    label: str = ""


# Every post-submission, non-terminal state: an abandoned or unsalvageable application always has an exit.
_REJECT_SOURCES = (
    S.APPLICATION_RECEIVED,
    S.UNDER_REVIEW,
    S.PENDING_PRE_SITE_RESUBMISSION,
    S.PRE_SITE_RESUBMITTED,
    S.SITE_VISIT_SCHEDULED,
    S.SITE_VISIT_DONE,
    S.AWAITING_POST_SITE_CLARIFICATION,
    S.PENDING_POST_SITE_RESUBMISSION,
    S.POST_SITE_CLARIFICATION_RESUBMITTED,
    S.PENDING_APPROVAL,
)

# Every post-submission, non-terminal state: the operator may withdraw at any point before a decision.
_WITHDRAW_SOURCES = (
    S.APPLICATION_RECEIVED,
    S.UNDER_REVIEW,
    S.PENDING_PRE_SITE_RESUBMISSION,
    S.PRE_SITE_RESUBMITTED,
    S.SITE_VISIT_SCHEDULED,
    S.SITE_VISIT_DONE,
    S.AWAITING_POST_SITE_CLARIFICATION,
    S.PENDING_POST_SITE_RESUBMISSION,
    S.POST_SITE_CLARIFICATION_RESUBMITTED,
    S.PENDING_APPROVAL,
)

TRANSITIONS: tuple[Transition, ...] = (
    Transition(S.DRAFT, S.APPLICATION_RECEIVED, Actor.OPERATOR, _needs_complete, "Submit"),
    Transition(S.APPLICATION_RECEIVED, S.UNDER_REVIEW, Actor.OFFICER, None, "Start review"),
    Transition(S.PRE_SITE_RESUBMITTED, S.UNDER_REVIEW, Actor.OFFICER, None, "Start review"),
    Transition(
        S.UNDER_REVIEW,
        S.PENDING_PRE_SITE_RESUBMISSION,
        Actor.OFFICER,
        _needs_open_feedback,
        "Request resubmission",
    ),
    Transition(
        S.UNDER_REVIEW,
        S.SITE_VISIT_SCHEDULED,
        Actor.OFFICER,
        _needs_no_open_feedback,
        "Mark site visit scheduled",
    ),
    Transition(
        S.PENDING_PRE_SITE_RESUBMISSION,
        S.PRE_SITE_RESUBMITTED,
        Actor.OPERATOR,
        _needs_flagged_change,
        "Resubmit",
    ),
    Transition(
        S.SITE_VISIT_SCHEDULED,
        S.SITE_VISIT_DONE,
        Actor.OFFICER,
        _needs_visit_confirmed,
        "Mark site visit done",
    ),
    # Use case 3 (v0.4.0). The brief's grammar decides whose turn each post-site state is: after the
    # checklist is submitted the operator answers (Awaiting Post-Site Clarification, round 1); the
    # officer reviews in Post-Site Clarification Resubmitted; later rounds use Pending Post-Site
    # Resubmission (SCOPE.md assumption 18, RELEASE_PLAN_V0_4_0.md section 4.1).
    Transition(
        S.SITE_VISIT_DONE,
        S.AWAITING_POST_SITE_CLARIFICATION,
        Actor.SYSTEM,
        _needs_checklist_complete,
        "Checklist submitted",
    ),
    Transition(
        S.AWAITING_POST_SITE_CLARIFICATION,
        S.POST_SITE_CLARIFICATION_RESUBMITTED,
        Actor.OPERATOR,
        _needs_all_answered,
        "Send responses",
    ),
    Transition(
        S.AWAITING_POST_SITE_CLARIFICATION,
        S.PENDING_APPROVAL,
        Actor.OFFICER,
        _needs_nothing_open,
        "Route to approval",
    ),
    Transition(
        S.PENDING_POST_SITE_RESUBMISSION,
        S.POST_SITE_CLARIFICATION_RESUBMITTED,
        Actor.OPERATOR,
        _needs_all_answered,
        "Send responses",
    ),
    Transition(
        S.POST_SITE_CLARIFICATION_RESUBMITTED,
        S.PENDING_POST_SITE_RESUBMISSION,
        Actor.OFFICER,
        _needs_open_clarification,
        "Request another round",
    ),
    Transition(
        S.POST_SITE_CLARIFICATION_RESUBMITTED,
        S.PENDING_APPROVAL,
        Actor.OFFICER,
        _needs_nothing_open,
        "Route to approval",
    ),
    Transition(S.PENDING_APPROVAL, S.APPROVED, Actor.OFFICER, None, "Approve"),
    # An officer who notices something at the decision step can go back instead of rejecting.
    Transition(S.PENDING_APPROVAL, S.UNDER_REVIEW, Actor.OFFICER, None, "Return to review"),
)
TRANSITIONS += tuple(
    Transition(src, S.REJECTED, Actor.OFFICER, _needs_note, "Reject") for src in _REJECT_SOURCES
)
TRANSITIONS += tuple(
    Transition(src, S.WITHDRAWN, Actor.OPERATOR, None, "Withdraw") for src in _WITHDRAW_SOURCES
)

TERMINAL: frozenset[S] = frozenset({S.APPROVED, S.REJECTED, S.WITHDRAWN})

_INDEX: dict[tuple[S, S], Transition] = {(t.source, t.target): t for t in TRANSITIONS}


class TransitionError(Exception):
    """Raised by `transition`. `kind` is `invalid` (no such edge), `forbidden` (wrong actor) or `guard`."""

    def __init__(self, kind: str, message: str, allowed: list[S]) -> None:
        super().__init__(message)
        self.kind = kind
        self.message = message
        self.allowed = allowed


def actor_for_role(role: Role) -> Actor | None:
    if role == Role.OPERATOR:
        return Actor.OPERATOR
    if role == Role.OFFICER:
        return Actor.OFFICER
    return None  # admin has no transitions


def allowed_targets(status: S, actor: Actor) -> list[S]:
    return [t.target for t in TRANSITIONS if t.source == status and t.actor == actor]


def available_actions(status: S, actor: Actor | None, ctx: TransitionContext) -> list[dict[str, object]]:
    """Every edge for this actor from `status`, with whether its guard currently passes (UI hint).
    A viewer without an actor (the admin) gets an empty list: read-only by construction (ADR-014)."""
    out: list[dict[str, object]] = []
    if actor is None:
        return out
    for t in TRANSITIONS:
        if t.source != status or t.actor != actor:
            continue
        reason = t.guard(ctx) if t.guard else None
        out.append({"target": t.target, "label": t.label, "enabled": reason is None, "reason": reason})
    return out


def transition(status: S, target: S, actor: Actor, ctx: TransitionContext) -> S:
    """Validate and return the new status. Raises TransitionError; never mutates anything."""
    t = _INDEX.get((status, target))
    allowed = allowed_targets(status, actor)
    if t is None:
        raise TransitionError("invalid", f"Cannot move from {status.value} to {target.value}.", allowed)
    if t.actor != actor:
        raise TransitionError("forbidden", "This action is not available for your role.", allowed)
    if t.guard is not None:
        reason = t.guard(ctx)
        if reason is not None:
            raise TransitionError("guard", reason, allowed)
    return target


def is_terminal(status: S) -> bool:
    return status in TERMINAL


def can_withdraw(status: S) -> bool:
    """True when the owner may withdraw from this state (US-038)."""
    return status in _WITHDRAW_SOURCES
