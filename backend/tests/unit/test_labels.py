from app.domain.labels import label_for, officer_label, operator_label, tone_for
from app.models.enums import ApplicationStatus as S
from app.models.enums import Role

# Verbatim from the assessment's status table (internal status, officer label, operator label).
ASSESSMENT_TABLE = [
    ("application_received", "Application Received", "Submitted"),
    ("under_review", "Under Review", "Under Review"),
    ("pending_pre_site_resubmission", "Pending Pre-Site Resubmission", "Pending Pre-Site Resubmission"),
    ("pre_site_resubmitted", "Pre-Site Resubmitted", "Pre-Site Resubmitted"),
    ("site_visit_scheduled", "Site Visit Scheduled", "Pending Site Visit"),
    ("site_visit_done", "Site Visit Done", "Pending Post-Site Clarification"),
    (
        "awaiting_post_site_clarification",
        "Awaiting Post-Site Clarification",
        "Pending Post-Site Clarification",
    ),
    ("pending_post_site_resubmission", "Awaiting Post-Site Resubmission", "Pending Post-Site Resubmission"),
    ("post_site_clarification_resubmitted", "Post-Site Clarification Resubmitted", "Post-Site Resubmitted"),
    ("pending_approval", "Route to Approval", "Pending Approval"),
    ("approved", "Approved", "Approved"),
    ("rejected", "Rejected", "Rejected"),
]


def test_every_assessment_row_matches_exactly() -> None:
    assert len(ASSESSMENT_TABLE) == 12
    for code, officer, operator in ASSESSMENT_TABLE:
        status = S(code)
        assert officer_label(status) == officer
        assert operator_label(status) == operator


def test_every_status_has_a_label() -> None:
    for status in S:
        assert officer_label(status)
        assert operator_label(status)


def test_label_for_role() -> None:
    assert label_for(S.PENDING_APPROVAL, Role.OPERATOR) == "Pending Approval"
    assert label_for(S.PENDING_APPROVAL, Role.OFFICER) == "Route to Approval"
    assert label_for(S.PENDING_APPROVAL, Role.ADMIN) == "Route to Approval"
    assert label_for(S.APPLICATION_RECEIVED, Role.OPERATOR) == "Submitted"


def test_route_to_approval_never_reaches_operator() -> None:
    assert all(operator_label(s) != "Route to Approval" for s in S)


def test_tones() -> None:
    assert tone_for(S.DRAFT) == "neutral"
    assert tone_for(S.PENDING_PRE_SITE_RESUBMISSION) == "warning"
    assert tone_for(S.APPROVED) == "success"
    assert tone_for(S.REJECTED) == "error"
    assert tone_for(S.UNDER_REVIEW) == "info"
