"""Shared pieces of the abuse-case pack (US-105): one populated world with a tenant, a second tenant, an
officer and an administrator; the cookie-mode client; a scanner stand-in."""

import uuid
from collections.abc import Iterator
from dataclasses import dataclass, field

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.settings import get_settings
from app.infra.clamd import ScanResult
from app.main import create_app
from app.models import AuditEvent, Base, Document, User
from app.models.enums import Role
from app.services import scan as scan_module
from tests.factories import login, make_user
from tests.integration.test_clarification import _attach, _respond, _submitted
from tests.journeys import PDF

Headers = dict[str, str]

# Tables a request may touch without that being a write on a tenant's data: every authenticated request
# moves the session's last_seen_at.
VOLATILE_TABLES = {"user_sessions"}

FRONTEND = "https://dev.permitflow.space"


def fingerprint(db: Session) -> dict[str, list[str]]:
    """Every row of every table except the volatile ones, as text: equal fingerprints mean no write."""
    db.rollback()
    out: dict[str, list[str]] = {}
    for table in Base.metadata.sorted_tables:
        if table.name not in VOLATILE_TABLES:
            out[table.name] = sorted(str(tuple(row)) for row in db.execute(select(table)))
    return out


@dataclass
class World:
    """Operator A owns everything below; operator B is the other tenant. The case is submitted, the visit
    arranged and the checklist sent with three flagged items, so every operator route has a live id."""

    a: Headers
    b: Headers
    officer: Headers
    admin: Headers
    app_id: str
    ids: dict[str, str] = field(default_factory=dict)

    @property
    def anon(self) -> Headers:
        return {}


@pytest.fixture
def world(client: TestClient, db: Session) -> World:
    app_id, op_a, off = _submitted(client, db)
    make_user(db, "op-b@example.sg", Role.OPERATOR)
    make_user(db, "adm@example.sg", Role.ADMIN, protected=True)
    op_b, admin = login(client, "op-b@example.sg"), login(client, "adm@example.sg")

    view = client.get(f"/api/v1/applications/{app_id}/clarifications", headers=op_a).json()
    item = next(i for i in view["items"] if i["key"] == "coved_edges")
    answered = _respond(client, op_a, app_id, item["item_id"], "Coving done on 24 Sep.")
    assert answered.status_code == 200, answered.text
    response_id = next(i for i in answered.json()["items"] if i["key"] == "coved_edges")["responses"][0]["id"]
    attached = _attach(client, op_a, app_id, response_id, "coving.pdf", PDF)
    assert attached.status_code == 201, attached.text
    attachment_id = next(i for i in attached.json()["view"]["items"] if i["key"] == "coved_edges")[
        "responses"
    ][0]["attachments"][0]["id"]

    owner = db.scalar(select(User).where(User.email == "op@example.sg"))
    document = db.scalar(select(Document).where(Document.application_id == uuid.UUID(app_id)))
    event = db.scalar(select(AuditEvent))
    notifications = client.get("/api/v1/notifications", headers=op_a).json()["items"]
    assert owner and document and event and notifications, "the world is missing a row the routes need"
    return World(
        a=op_a,
        b=op_b,
        officer=off,
        admin=admin,
        app_id=app_id,
        ids={
            "application_id": app_id,
            "document_id": str(document.id),
            "item_id": item["item_id"],
            "response_id": response_id,
            "attachment_id": attachment_id,
            "notification_id": notifications[0]["id"],
            "user_id": str(owner.id),
            "event_id": str(event.id),
            "feedback_id": str(uuid.uuid4()),  # officer-only routes: the role guard answers first
        },
    )


@pytest.fixture
def cookie_app(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    """The app in AUTH_MODE=cookie, talking https (the cookies are Secure)."""
    settings = get_settings()
    monkeypatch.setattr(settings, "auth_mode", "cookie")
    monkeypatch.setattr(settings, "cors_origins", f"{FRONTEND},https://other.permitflow.space")
    with TestClient(create_app(), base_url="https://testserver") as c:
        yield c


class CleanScanner:
    """Stands in for the clamd socket: everything is clean."""

    def scan(self, data: bytes) -> ScanResult:
        return ScanResult(infected=False)


@pytest.fixture
def scan_enforced(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(get_settings(), "scan_mode", "enforce")
    monkeypatch.setattr(scan_module, "client_from_settings", lambda: CleanScanner())
