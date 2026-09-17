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
    is_terminal,
    transition,
)
from app.models.enums import ApplicationStatus as S
from app.models.enums import Role

ALL_OK = TransitionContext(
    open_feedback_count=1, has_changes_to_flagged_targets=True, is_complete=True, has_note=True
)
VALID = {(t.source, t.target, t.actor) for t in TRANSITIONS}


@pytest.mark.parametrize("source,target,actor", list(itertools.product(S, S, Actor)))
def test_every_combination(source: S, target: S, actor: Actor) -> None:
    edge_exists = any(t.source == source and t.target == target for t in TRANSITIONS)
    if (source, target, actor) in VALID:
        # a permissive context passes every guard except "no open feedback" (site visit)
        ctx = (
            ALL_OK if target != S.SITE_VISIT_SCHEDULED else TransitionContext(is_complete=True, has_note=True)
        )
        assert transition(source, target, actor, ctx) == target
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
    for s in (S.APPROVED, S.REJECTED):
        assert is_terminal(s)
        assert not [t for t in TRANSITIONS if t.source == s]


def test_reject_possible_from_every_non_terminal_post_submission_state() -> None:
    for s in S:
        if s in (S.DRAFT, S.APPROVED, S.REJECTED):
            continue
        if s in (
            S.AWAITING_POST_SITE_CLARIFICATION,
            S.PENDING_POST_SITE_RESUBMISSION,
            S.POST_SITE_CLARIFICATION_RESUBMITTED,
        ):
            continue  # UC3 states, deferred: reject edges are added with UC3
        assert S.REJECTED in allowed_targets(s, Actor.OFFICER), s


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
