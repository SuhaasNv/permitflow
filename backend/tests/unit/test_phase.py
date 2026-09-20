"""US-083: the stage and the outcome read from the status, one rule for every screen."""

from app.domain.enums import ApplicationStatus as S
from app.domain.phase import outcome_for, phase_for


def test_every_status_has_a_phase_and_only_the_decided_ones_an_outcome() -> None:
    expected = {
        S.DRAFT: ("draft", None),
        S.APPLICATION_RECEIVED: ("pre_site", None),
        S.UNDER_REVIEW: ("pre_site", None),
        S.PENDING_PRE_SITE_RESUBMISSION: ("pre_site", None),
        S.PRE_SITE_RESUBMITTED: ("pre_site", None),
        S.SITE_VISIT_SCHEDULED: ("site_visit", None),
        S.SITE_VISIT_DONE: ("site_visit", None),
        S.AWAITING_POST_SITE_CLARIFICATION: ("post_site", None),
        S.PENDING_POST_SITE_RESUBMISSION: ("post_site", None),
        S.POST_SITE_CLARIFICATION_RESUBMITTED: ("post_site", None),
        S.PENDING_APPROVAL: ("decision", None),
        S.APPROVED: ("decided", "approved"),
        S.REJECTED: ("decided", "rejected"),
        S.WITHDRAWN: ("decided", "withdrawn"),
    }
    assert set(expected) == set(S)
    for status, (phase, outcome) in expected.items():
        assert (phase_for(status), outcome_for(status)) == (phase, outcome), status
