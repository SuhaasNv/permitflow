"""Role-safe wording for a refused operator action (FR-026, ADR-005). Pure Python.

`domain/workflow.py` explains a refusal in internal terms ("Cannot move from pending_approval to
pre_site_resubmitted"). An operator response must never carry an internal status code or an
officer-only label, so operator services translate the refusal here: the operator's own label for
the current status plus what the action needs."""

from app.domain.enums import ApplicationStatus
from app.domain.labels import operator_label

_REQUIREMENT = {
    "submit": "Only a draft can be submitted.",
    "resubmit": "A resubmission is only possible while the office is waiting for your changes.",
    "withdraw": "Only an application the office is still working on can be withdrawn.",
}


def refusal(status: ApplicationStatus, action: str) -> str:
    """One sentence for the operator: where the application is, and what the action needs."""
    where = f"This application is {operator_label(status)}."
    return f"{where} {_REQUIREMENT[action]}"
