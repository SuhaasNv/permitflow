"""Human-readable summaries for audit events (FR-025). Pure: event type + payload → one sentence."""

from typing import Any

from app.domain.enums import ApplicationStatus
from app.domain.labels import officer_label


def _status(value: Any) -> str:
    try:
        return officer_label(ApplicationStatus(str(value)))
    except ValueError:
        return str(value)


def summarize(event_type: str, payload: dict[str, Any]) -> str:
    p = payload
    match event_type:
        case "application.created":
            return f"Application {p.get('reference_no', '')} created".strip()
        case "section.updated":
            fields = p.get("fields") or []
            n = len(fields)
            return f"Section '{p.get('section', '')}' saved ({n} {'field' if n == 1 else 'fields'} changed)"
        case "document.uploaded":
            return f"Document uploaded: {p.get('document_type', '')} ({p.get('filename', '')})".replace(
                " ()", ""
            )
        case "document.replaced":
            return f"Document replaced: {p.get('document_type', '')}"
        case "document.deleted":
            return f"Document removed: {p.get('document_type', '')}"
        case "verification.requested":
            return f"Check re-run requested for {p.get('document_type', '')}"
        case "verification.completed":
            return f"Check finished: {p.get('status', '')}" + (
                f" ({p['provider']})" if p.get("provider") else ""
            )
        case "revision.submitted":
            number = p.get("revision_number")
            changed = len(p.get("changed_sections") or []) + len(p.get("changed_document_types") or [])
            if number == 1:
                return "Revision 1 submitted"
            return (
                f"Revision {number} resubmitted ({changed} {'target' if changed == 1 else 'targets'} changed)"
            )
        case "status.changed":
            return f"Status: {_status(p.get('from'))} → {_status(p.get('to'))}"
        case "feedback.created":
            return f"Feedback added on {p.get('target', '')}"
        case "feedback.withdrawn":
            return f"Feedback withdrawn on {p.get('target', '')}"
        case "feedback.released":
            ids = p.get("feedback_ids") or []
            return f"{len(ids)} feedback {'item' if len(ids) == 1 else 'items'} sent to the operator"
        case "feedback.addressed":
            return f"Feedback on {p.get('target', '')} addressed in Revision {p.get('revision_number', '')}"
        case "feedback.resolved":
            return f"Feedback on {p.get('target', '')} resolved"
        case "feedback.reopened":
            return f"Feedback on {p.get('target', '')} marked not fixed (open again)"
        case "licence.issued":
            return f"Licence {p.get('licence_no', '')} issued, valid to {p.get('valid_to', '')}"
        case "feedback.restored":
            return f"Feedback on {p.get('target', '')} restored to {p.get('to', '')} (undo)"
        case _:
            return event_type
