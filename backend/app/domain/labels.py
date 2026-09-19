"""Role-specific status labels, verbatim from the assessment table (STATE_MACHINE.md).

The operator API returns only `label_for(status, Role.OPERATOR)`; the internal code never reaches an
operator client (ADR-005, FR-008, FR-026).
"""

from app.domain.enums import ApplicationStatus as S
from app.domain.enums import Role

# status -> (officer label, operator label)
_LABELS: dict[S, tuple[str, str]] = {
    S.DRAFT: ("Draft", "Draft"),
    S.APPLICATION_RECEIVED: ("Application Received", "Submitted"),
    S.UNDER_REVIEW: ("Under Review", "Under Review"),
    S.PENDING_PRE_SITE_RESUBMISSION: ("Pending Pre-Site Resubmission", "Pending Pre-Site Resubmission"),
    S.PRE_SITE_RESUBMITTED: ("Pre-Site Resubmitted", "Pre-Site Resubmitted"),
    S.SITE_VISIT_SCHEDULED: ("Site Visit Scheduled", "Pending Site Visit"),
    S.SITE_VISIT_DONE: ("Site Visit Done", "Pending Post-Site Clarification"),
    S.AWAITING_POST_SITE_CLARIFICATION: (
        "Awaiting Post-Site Clarification",
        "Pending Post-Site Clarification",
    ),
    S.PENDING_POST_SITE_RESUBMISSION: (
        "Awaiting Post-Site Resubmission",
        "Pending Post-Site Resubmission",
    ),
    S.POST_SITE_CLARIFICATION_RESUBMITTED: (
        "Post-Site Clarification Resubmitted",
        "Post-Site Resubmitted",
    ),
    S.PENDING_APPROVAL: ("Route to Approval", "Pending Approval"),
    S.APPROVED: ("Approved", "Approved"),
    S.REJECTED: ("Rejected", "Rejected"),
    S.WITHDRAWN: ("Withdrawn", "Withdrawn"),
}


def officer_label(status: S) -> str:
    return _LABELS[status][0]


def operator_label(status: S) -> str:
    return _LABELS[status][1]


def label_for(status: S, role: Role) -> str:
    """Officers and admins see the internal wording; operators see theirs."""
    return operator_label(status) if role == Role.OPERATOR else officer_label(status)


# Badge colour group used by the UI (DESIGN_SYSTEM.md). Served so the client never maps codes.
def tone_for(status: S) -> str:
    if status in (S.DRAFT, S.WITHDRAWN):
        return "neutral"
    if status in (S.PENDING_PRE_SITE_RESUBMISSION, S.PENDING_POST_SITE_RESUBMISSION):
        return "warning"
    if status == S.APPROVED:
        return "success"
    if status == S.REJECTED:
        return "error"
    return "info"
