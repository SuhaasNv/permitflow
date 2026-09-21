"""Every (state, target, actor) combination is exercised (SPRINTS.md Sprint 1 exit criteria)."""

import itertools

import pytest

from app.domain.workflow import (
    TRANSITIONS,
    Actor,
    TransitionContext,
    TransitionError,
    actor_for_role,
    allowed_targets,
    available_actions,
    can_withdraw,
    is_terminal,
    transition,
)
from app.models.enums import ApplicationStatus as S
from app.models.enums import Role

ALL_OK = TransitionContext(
    open_feedback_count=1,
    has_changes_to_flagged_targets=True,
    is_complete=True,
    has_note=True,
    checklist_complete=True,
    open_clarification_count=1,
    answered_clarification_count=0,
    all_open_items_answered=True,
    visit_confirmed=True,
)
VALID = {(t.source, t.target, t.actor) for t in TRANSITIONS}


def permissive_context(target: S) -> TransitionContext:
    """A context that passes every guard on the way to `target`. Two guards want the opposite of
    the permissive default: a site visit needs no open feedback, and routing to approval needs no
    clarification item open or answered."""
    if target == S.SITE_VISIT_SCHEDULED:
        return TransitionContext(is_complete=True, has_note=True)
    if target == S.PENDING_APPROVAL:
        return TransitionContext(has_note=True, open_clarification_count=0, answered_clarification_count=0)
    return ALL_OK


@pytest.mark.parametrize("source,target,actor", list(itertools.product(S, S, Actor)))
def test_every_combination(source: S, target: S, actor: Actor) -> None:
    edge_exists = any(t.source == source and t.target == target for t in TRANSITIONS)
    if (source, target, actor) in VALID:
        assert transition(source, target, actor, permissive_context(target)) == target
    elif edge_exists:
        with pytest.raises(TransitionError) as exc:
            transition(source, target, actor, ALL_OK)
        assert exc.value.kind == "forbidden"
    else:
        with pytest.raises(TransitionError) as exc:
            transition(source, target, actor, ALL_OK)
        assert exc.value.kind == "invalid"
        assert exc.value.allowed == allowed_targets(source, actor)


def test_terminal_states_have_no_outgoing_edges() -> None:
    for s in (S.APPROVED, S.REJECTED, S.WITHDRAWN):
        assert is_terminal(s)
        assert not [t for t in TRANSITIONS if t.source == s]


def test_withdraw_possible_from_every_non_terminal_post_submission_state() -> None:
    for s in S:
        if s in (S.DRAFT, S.APPROVED, S.REJECTED, S.WITHDRAWN):
            assert not can_withdraw(s)
            assert S.WITHDRAWN not in allowed_targets(s, Actor.OPERATOR), s
            continue
        assert can_withdraw(s)
        assert S.WITHDRAWN in allowed_targets(s, Actor.OPERATOR), s
        # officers never withdraw on the operator's behalf
        assert S.WITHDRAWN not in allowed_targets(s, Actor.OFFICER), s
        assert transition(s, S.WITHDRAWN, Actor.OPERATOR, TransitionContext()) == S.WITHDRAWN


def test_reject_possible_from_every_non_terminal_post_submission_state() -> None:
    for s in S:
        if s in (S.DRAFT, S.APPROVED, S.REJECTED, S.WITHDRAWN):
            continue
        # including the three post-site states since US-079: a case never gets stuck after a visit
        assert S.REJECTED in allowed_targets(s, Actor.OFFICER), s
        with pytest.raises(TransitionError) as exc:
            transition(s, S.REJECTED, Actor.OFFICER, TransitionContext(has_note=False))
        assert exc.value.kind == "guard"


def test_post_site_edges_follow_the_brief_reading() -> None:
    """After the checklist the operator answers; the officer reviews the answers; later rounds use
    Pending Post-Site Resubmission (SCOPE.md assumption 18)."""
    assert allowed_targets(S.AWAITING_POST_SITE_CLARIFICATION, Actor.OPERATOR) == [
        S.POST_SITE_CLARIFICATION_RESUBMITTED,
        S.WITHDRAWN,
    ]
    assert S.PENDING_POST_SITE_RESUBMISSION not in allowed_targets(
        S.AWAITING_POST_SITE_CLARIFICATION, Actor.OFFICER
    )
    assert allowed_targets(S.POST_SITE_CLARIFICATION_RESUBMITTED, Actor.OFFICER) == [
        S.PENDING_POST_SITE_RESUBMISSION,
        S.PENDING_APPROVAL,
        S.REJECTED,
    ]
    assert S.AWAITING_POST_SITE_CLARIFICATION not in allowed_targets(
        S.POST_SITE_CLARIFICATION_RESUBMITTED, Actor.OFFICER
    )
    assert allowed_targets(S.SITE_VISIT_DONE, Actor.SYSTEM) == [S.AWAITING_POST_SITE_CLARIFICATION]


def test_clarification_guards() -> None:
    # the checklist submit needs a complete checklist
    with pytest.raises(TransitionError) as e:
        transition(
            S.SITE_VISIT_DONE,
            S.AWAITING_POST_SITE_CLARIFICATION,
            Actor.SYSTEM,
            TransitionContext(checklist_complete=False),
        )
    assert e.value.kind == "guard"
    assert transition(
        S.SITE_VISIT_DONE,
        S.AWAITING_POST_SITE_CLARIFICATION,
        Actor.SYSTEM,
        TransitionContext(checklist_complete=True),
    )
    # since US-063 there is no route from Site Visit Done straight to approval: the checklist is the way
    with pytest.raises(TransitionError):
        transition(S.SITE_VISIT_DONE, S.PENDING_APPROVAL, Actor.OFFICER, TransitionContext())
    # the operator sends only when every open item is answered
    for src in (S.AWAITING_POST_SITE_CLARIFICATION, S.PENDING_POST_SITE_RESUBMISSION):
        with pytest.raises(TransitionError):
            transition(
                src,
                S.POST_SITE_CLARIFICATION_RESUBMITTED,
                Actor.OPERATOR,
                TransitionContext(all_open_items_answered=False),
            )
        assert transition(
            src,
            S.POST_SITE_CLARIFICATION_RESUBMITTED,
            Actor.OPERATOR,
            TransitionContext(all_open_items_answered=True),
        )
    # another round needs an open item; approval needs nothing open or answered
    with pytest.raises(TransitionError):
        transition(
            S.POST_SITE_CLARIFICATION_RESUBMITTED,
            S.PENDING_POST_SITE_RESUBMISSION,
            Actor.OFFICER,
            TransitionContext(open_clarification_count=0),
        )
    # ... from every state the operator answers in or the officer reviews in, so a round whose
    # questions were all withdrawn never leaves Reject as the only move (UAT, 21 Sep)
    for src in (
        S.AWAITING_POST_SITE_CLARIFICATION,
        S.PENDING_POST_SITE_RESUBMISSION,
        S.POST_SITE_CLARIFICATION_RESUBMITTED,
    ):
        for ctx in (
            TransitionContext(open_clarification_count=1),
            TransitionContext(answered_clarification_count=1),
        ):
            with pytest.raises(TransitionError):
                transition(src, S.PENDING_APPROVAL, Actor.OFFICER, ctx)
        assert transition(src, S.PENDING_APPROVAL, Actor.OFFICER, TransitionContext())


def test_admin_sees_no_actions() -> None:
    assert available_actions(S.UNDER_REVIEW, None, TransitionContext()) == []
    assert available_actions(S.POST_SITE_CLARIFICATION_RESUBMITTED, None, ALL_OK) == []


def test_guards() -> None:
    with pytest.raises(TransitionError) as e:
        transition(S.DRAFT, S.APPLICATION_RECEIVED, Actor.OPERATOR, TransitionContext(is_complete=False))
    assert e.value.kind == "guard"

    with pytest.raises(TransitionError):
        transition(
            S.UNDER_REVIEW,
            S.PENDING_PRE_SITE_RESUBMISSION,
            Actor.OFFICER,
            TransitionContext(open_feedback_count=0),
        )

    with pytest.raises(TransitionError):
        transition(
            S.UNDER_REVIEW, S.SITE_VISIT_SCHEDULED, Actor.OFFICER, TransitionContext(open_feedback_count=2)
        )
    # addressed items do not block: only open ones count, and the caller passes only open ones
    assert transition(
        S.UNDER_REVIEW, S.SITE_VISIT_SCHEDULED, Actor.OFFICER, TransitionContext(open_feedback_count=0)
    )

    with pytest.raises(TransitionError):
        transition(
            S.PENDING_PRE_SITE_RESUBMISSION, S.PRE_SITE_RESUBMITTED, Actor.OPERATOR, TransitionContext()
        )

    with pytest.raises(TransitionError):
        transition(S.UNDER_REVIEW, S.REJECTED, Actor.OFFICER, TransitionContext(has_note=False))

    # the visit is marked done only once the appointment is confirmed (US-084)
    with pytest.raises(TransitionError) as e:
        transition(S.SITE_VISIT_SCHEDULED, S.SITE_VISIT_DONE, Actor.OFFICER, TransitionContext())
    assert "Confirm the visit date" in e.value.message
    assert transition(
        S.SITE_VISIT_SCHEDULED, S.SITE_VISIT_DONE, Actor.OFFICER, TransitionContext(visit_confirmed=True)
    )


def test_available_actions_reports_disabled_reasons() -> None:
    actions = available_actions(S.UNDER_REVIEW, Actor.OFFICER, TransitionContext(open_feedback_count=0))
    by_target = {a["target"]: a for a in actions}
    assert by_target[S.SITE_VISIT_SCHEDULED]["enabled"] is True
    assert by_target[S.PENDING_PRE_SITE_RESUBMISSION]["enabled"] is False
    assert "open feedback" in str(by_target[S.PENDING_PRE_SITE_RESUBMISSION]["reason"])
    assert by_target[S.REJECTED]["enabled"] is False


def test_actor_for_role() -> None:
    assert actor_for_role(Role.OPERATOR) == Actor.OPERATOR
    assert actor_for_role(Role.OFFICER) == Actor.OFFICER
    assert actor_for_role(Role.ADMIN) is None
