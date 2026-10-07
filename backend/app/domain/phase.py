"""The stage a case is in and how it ended, read from the status (US-083). The screens branch on these
two words instead of on label or tone strings, so a renamed label never breaks a branch."""

from app.domain.enums import ApplicationStatus as S

PRE_SITE = frozenset(
    {S.APPLICATION_RECEIVED, S.UNDER_REVIEW, S.PENDING_PRE_SITE_RESUBMISSION, S.PRE_SITE_RESUBMITTED}
)
SITE_VISIT = frozenset({S.SITE_VISIT_SCHEDULED, S.SITE_VISIT_DONE})
POST_SITE = frozenset(
    {
        S.AWAITING_POST_SITE_CLARIFICATION,
        S.PENDING_POST_SITE_RESUBMISSION,
        S.POST_SITE_CLARIFICATION_RESUBMITTED,
    }
)
DECISION = frozenset({S.PENDING_APPROVAL})
DECIDED = frozenset({S.APPROVED, S.REJECTED, S.WITHDRAWN})


def phase_for(status: S) -> str:
    """draft | pre_site | site_visit | post_site | decision | decided"""
    if status == S.DRAFT:
        return "draft"
    if status in PRE_SITE:
        return "pre_site"
    if status in SITE_VISIT:
        return "site_visit"
    if status in POST_SITE:
        return "post_site"
    if status in DECISION:
        return "decision"
    return "decided"


def outcome_for(status: S) -> str | None:
    """approved | rejected | withdrawn, or None while the case is open."""
    return status.value if status in DECIDED else None


__all__ = ["outcome_for", "phase_for"]
