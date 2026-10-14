"""The explicit allow-table behind abuse case 1 (US-105, threat T1, T3, T8, SEC-003, SEC-004).

Every route of the app has one row: which roles may call it and what its data is scoped to. The matrix test
reads the routes from the app, so a new route that is missing here fails `test_every_route_has_a_row` with
the line to add. The rows are deliberately written out and not derived from the route guards: the guards are
what is under test.

scope:
  public      no sign-in needed (sign-in, health probe, metrics scrape).
  open        not tied to one tenant's data: any listed role gets the same answer.
  self        scoped inside the query to the caller (own list, own notifications, own session).
  own         the path names one operator's resource: another operator is refused with 403 or 404, never 2xx.
  owner_user  the path names one user's row (a notification): every other principal gets 404.
"""

from typing import Literal

OP, OFF, ADM = "operator", "officer", "admin"

Scope = Literal["public", "open", "self", "own", "owner_user"]
Row = tuple[frozenset[str], Scope]

NOBODY: frozenset[str] = frozenset()
EVERYONE = frozenset({OP, OFF, ADM})
OPERATOR = frozenset({OP})
OFFICER = frozenset({OFF})
OFFICER_ADMIN = frozenset({OFF, ADM})
ADMIN = frozenset({ADM})

A = "/applications/{application_id}"
O = "/officer/applications/{application_id}"  # noqa: E741 - the officer prefix, kept short for the table

ACCESS: dict[tuple[str, str], Row] = {
    # public
    ("GET", "/health"): (NOBODY, "public"),
    ("GET", "/metrics"): (NOBODY, "public"),
    ("POST", "/auth/login"): (NOBODY, "public"),
    # any signed-in user
    ("GET", "/auth/me"): (EVERYONE, "self"),
    ("POST", "/auth/logout"): (EVERYONE, "self"),
    ("GET", "/form-schema"): (EVERYONE, "open"),
    ("GET", "/notifications"): (EVERYONE, "self"),
    ("POST", "/notifications/read-all"): (EVERYONE, "self"),
    ("POST", "/notifications/{notification_id}/read"): (EVERYONE, "owner_user"),
    # operator
    ("GET", "/applications"): (OPERATOR, "self"),
    ("POST", "/applications"): (OPERATOR, "self"),
    ("GET", A): (OPERATOR, "own"),
    ("POST", A + "/submit"): (OPERATOR, "own"),
    ("GET", A + "/compare"): (EVERYONE, "own"),
    ("POST", A + "/resubmit"): (OPERATOR, "own"),
    ("GET", A + "/licence"): (EVERYONE, "own"),
    ("DELETE", A): (OPERATOR, "own"),
    ("POST", A + "/withdraw"): (OPERATOR, "own"),
    ("POST", A + "/site-visit/accept"): (OPERATOR, "own"),
    ("POST", A + "/site-visit/counter"): (OPERATOR, "own"),
    ("POST", A + "/site-visit/reschedule"): (OPERATOR, "own"),
    ("GET", A + "/clarifications"): (OPERATOR, "own"),
    ("POST", A + "/clarifications/{item_id}/responses"): (OPERATOR, "own"),
    ("POST", A + "/clarifications/responses/{response_id}/attachments"): (OPERATOR, "own"),
    ("DELETE", A + "/clarifications/responses/{response_id}/attachments/{attachment_id}"): (OPERATOR, "own"),
    ("POST", A + "/clarifications/send"): (OPERATOR, "own"),
    ("GET", A + "/clarifications/attachments/{attachment_id}/download"): (EVERYONE, "own"),
    ("PATCH", A + "/sections/{key}"): (OPERATOR, "own"),
    ("POST", A + "/documents"): (OPERATOR, "own"),
    ("DELETE", A + "/documents/{document_id}"): (OPERATOR, "own"),
    ("GET", A + "/documents/{document_id}/download"): (EVERYONE, "own"),
    ("POST", A + "/documents/{document_id}/verify"): (OPERATOR, "own"),
    # officer (reads also open to the administrator)
    ("GET", "/officer/applications"): (OFFICER_ADMIN, "open"),
    ("GET", O): (OFFICER_ADMIN, "open"),
    ("POST", O + "/transition"): (OFFICER, "open"),
    ("POST", O + "/documents/{document_id}/verify"): (OFFICER, "open"),
    ("GET", "/officer/feedback-templates"): (OFFICER, "open"),
    ("POST", O + "/feedback"): (OFFICER, "open"),
    ("POST", O + "/feedback/{feedback_id}/withdraw"): (OFFICER, "open"),
    ("POST", O + "/feedback/{feedback_id}/resolve"): (OFFICER, "open"),
    ("POST", O + "/feedback/{feedback_id}/reopen"): (OFFICER, "open"),
    ("POST", O + "/feedback/{feedback_id}/restore"): (OFFICER, "open"),
    ("GET", O + "/licence/preview"): (OFFICER, "open"),
    ("POST", O + "/site-visit"): (OFFICER, "open"),
    ("POST", O + "/site-visit/decide"): (OFFICER, "open"),
    ("POST", O + "/site-visit/confirm"): (OFFICER, "open"),
    ("POST", O + "/site-visit/reschedule"): (OFFICER, "open"),
    ("GET", O + "/audit"): (OFFICER_ADMIN, "open"),
    ("POST", O + "/clarifications/{item_id}/resolve"): (OFFICER, "open"),
    ("POST", O + "/clarifications/{item_id}/reopen"): (OFFICER, "open"),
    ("POST", O + "/clarifications/{item_id}/withdraw"): (OFFICER, "open"),
    ("POST", O + "/clarifications/{item_id}/restore"): (OFFICER, "open"),
    ("GET", "/checklist-schema"): (OFFICER_ADMIN, "open"),
    ("POST", O + "/checklist"): (OFFICER, "open"),
    ("GET", O + "/checklist"): (OFFICER_ADMIN, "open"),
    ("PUT", O + "/checklist"): (OFFICER, "open"),
    ("POST", O + "/checklist/submit"): (OFFICER, "open"),
    # administrator (read-only on cases; user management and settings are the only writes)
    ("GET", "/admin/overview"): (ADMIN, "open"),
    ("GET", "/admin/audit-feed"): (ADMIN, "open"),
    ("GET", "/admin/applications/{application_id}"): (ADMIN, "open"),
    ("GET", "/admin/users"): (ADMIN, "open"),
    ("POST", "/admin/users"): (ADMIN, "open"),
    ("PATCH", "/admin/users/{user_id}"): (ADMIN, "open"),
    ("GET", "/admin/settings"): (ADMIN, "open"),
    ("GET", "/admin/settings/history"): (ADMIN, "open"),
    ("PUT", "/admin/settings/{key}"): (ADMIN, "open"),
    ("POST", "/admin/settings/history/{event_id}/revert"): (ADMIN, "open"),
    ("GET", "/admin/ai-usage"): (ADMIN, "open"),
    ("GET", "/admin/ai-usage.csv"): (ADMIN, "open"),
}

# Required query strings: without them a 422 would hide the ownership check from the other operator.
QUERY: dict[tuple[str, str], dict[str, int]] = {("GET", A + "/compare"): {"from": 1, "to": 2}}

# Safe routes where the owner is expected to get something other than 200, and why. Anything else that
# answers the owner with a 404 means the matrix is not reaching the resource it claims to test.
OWNER_NOT_200: dict[tuple[str, str], tuple[int, str]] = {
    ("GET", A + "/licence"): (404, "no licence is issued before approval"),
    ("GET", A + "/compare"): (404, "the case has a single revision, so revision 2 does not exist"),
}
