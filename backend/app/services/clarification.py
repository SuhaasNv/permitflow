"""The post-site clarification rounds (US-064 to US-066). The operator's side: the view of the items
with a released request, in operator words (US-064); the responses, their attachments and the send that
moves the case (US-065). Every mutation locks the application row first (ADR-008); the officer's
decisions live in US-066."""

import hashlib
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime
from typing import BinaryIO

from sqlalchemy.orm import Session

from app.core.errors import BadRequest, Conflict, NotFound, ValidationFailed
from app.core.settings import get_settings
from app.domain.checklist_schema import ITEM_BY_KEY, item_title
from app.domain.enums import ApplicationStatus, ClarificationStatus, NotificationKind
from app.domain.uploads import (
    UploadRejected,
    canonical_content_type,
    check_magic_bytes,
    check_name_and_type,
    too_large_message,
)
from app.domain.workflow import Actor
from app.infra.storage import FileStorage, get_storage, new_storage_key
from app.models import (
    Application,
    ChecklistItem,
    ClarificationAttachment,
    ClarificationRequest,
    ClarificationResponse,
    User,
)
from app.repositories.applications import ApplicationRepository
from app.repositories.audit import AuditRepository
from app.repositories.checklists import ChecklistRepository
from app.schemas.clarification import (
    ClarificationAttachmentOut,
    ClarificationBlock,
    ClarificationItemOut,
    ClarificationOfficerView,
    ClarificationOperatorView,
    ClarificationRequestOut,
    ClarificationResponseOut,
    ClarificationThreadOut,
    ClarificationThreadRequestOut,
)
from app.services.documents import CHUNK, _display_name
from app.services.notifications import NotificationService

MAX_MESSAGE = 2000
ATTACHMENT_CAP = 3

OPERATOR_TURN_STATES = (
    ApplicationStatus.AWAITING_POST_SITE_CLARIFICATION,
    ApplicationStatus.PENDING_POST_SITE_RESUBMISSION,
)

OPERATOR_WORDS: dict[ClarificationStatus, str] = {
    ClarificationStatus.OPEN: "Waiting for your response",
    ClarificationStatus.ANSWERED: "Sent",
    ClarificationStatus.RESOLVED: "Clarified",
    ClarificationStatus.WITHDRAWN: "No longer needed",
    ClarificationStatus.NONE: "",
}


class ClarificationService:
    def __init__(self, db: Session, storage: FileStorage | None = None) -> None:
        self.db = db
        self.storage = storage or get_storage()
        self.applications = ApplicationRepository(db)
        self.checklists = ChecklistRepository(db)
        self.audit = AuditRepository(db)
        self.notifications = NotificationService(db)

    def operator_view(self, operator: User, application_id: uuid.UUID) -> ClarificationOperatorView:
        app = self.applications.get_for(operator, application_id)
        return self.build(app)

    def build(self, app: Application) -> ClarificationOperatorView:
        checklist = self.checklists.current_for(app.id)
        if checklist is None:
            return ClarificationOperatorView(
                application_id=app.id,
                visit_no=None,
                items=[],
                open_count=0,
                answered_count=0,
                resolved_count=0,
                round=0,
                can_respond=False,
                can_send=False,
            )
        items = self.checklists.items_for(checklist.id)
        requests = self.checklists.requests_for_items([i.id for i in items])
        responses = self.checklists.responses_for_requests([q.id for q in requests])
        attachments = self.checklists.attachments_for_responses([r.id for r in responses.values()])
        by_item: dict[uuid.UUID, list[ClarificationRequest]] = {}
        for q in requests:
            by_item.setdefault(q.item_id, []).append(q)
        out: list[ClarificationItemOut] = []
        drafted_every_open = True
        for item in items:
            released = [
                q for q in by_item.get(item.id, []) if q.released_at is not None and q.withdrawn_at is None
            ]
            if not released:
                continue  # unflagged, or only unreleased questions: not the operator's business yet
            out.append(self._item_out(app, item, released, responses, attachments))
            if item.clarification_status == ClarificationStatus.OPEN:
                drafted = responses.get(released[-1].id)
                if drafted is None or not drafted.message.strip():
                    drafted_every_open = False
        open_count = sum(1 for i in out if i.status == OPERATOR_WORDS[ClarificationStatus.OPEN])
        answered = sum(1 for i in out if i.status == OPERATOR_WORDS[ClarificationStatus.ANSWERED])
        resolved = sum(1 for i in out if i.status == OPERATOR_WORDS[ClarificationStatus.RESOLVED])
        operator_turn = app.status in OPERATOR_TURN_STATES
        return ClarificationOperatorView(
            application_id=app.id,
            visit_no=checklist.visit_no,
            items=out,
            open_count=open_count,
            answered_count=answered,
            resolved_count=resolved,
            round=max((i.round_no for i in out), default=0),
            can_respond=operator_turn and open_count > 0,
            can_send=operator_turn and open_count > 0 and drafted_every_open,
        )

    def block(self, app: Application) -> ClarificationBlock | None:
        """The application view's block; None before any item was released to the operator."""
        view = self.build(app)
        if not view.items:
            return None
        return ClarificationBlock(
            can_respond=view.can_respond,
            open_count=view.open_count,
            answered_count=view.answered_count,
            round=view.round,
        )

    def open_counts(self, app_ids: list[uuid.UUID]) -> dict[uuid.UUID, int]:
        """Items waiting for the operator per application (the list and the dashboard)."""
        checklists = self.checklists.current_for_many(app_ids)
        out: dict[uuid.UUID, int] = {}
        for app_id, checklist in checklists.items():
            items = self.checklists.items_for(checklist.id)
            out[app_id] = sum(1 for i in items if i.clarification_status == ClarificationStatus.OPEN)
        return out

    def _item_out(
        self,
        app: Application,
        item: ChecklistItem,
        released: list[ClarificationRequest],
        responses: dict[uuid.UUID, ClarificationResponse],
        attachments: dict[uuid.UUID, list[ClarificationAttachment]],
    ) -> ClarificationItemOut:
        current_round = max(q.round_no for q in released)
        definition = ITEM_BY_KEY.get(item.item_key)
        parent = ITEM_BY_KEY.get(item.parent_key or "")
        title = item_title(item.item_key, item.custom_title)
        if item.is_extra and parent is not None:
            title = f"{parent.title}: {title}"
        status = item.clarification_status
        answers: list[ClarificationResponseOut] = []
        for q in released:
            r = responses.get(q.id)
            if r is None:
                continue
            answers.append(
                ClarificationResponseOut(
                    id=r.id,
                    round_no=q.round_no,
                    message=r.message,
                    created_at=r.created_at,
                    sent_at=r.sent_at,
                    attachments=[
                        ClarificationAttachmentOut(
                            id=a.id,
                            original_filename=a.original_filename,
                            content_type=a.content_type,
                            size_bytes=a.size_bytes,
                            uploaded_at=a.uploaded_at,
                        )
                        for a in attachments.get(r.id, [])
                    ],
                )
            )
        return ClarificationItemOut(
            item_id=item.id,
            key=item.item_key,
            title=title,
            guidance=definition.guidance if definition else "",
            status=OPERATOR_WORDS.get(status, ""),
            round_no=current_round,
            requests=[
                ClarificationRequestOut(
                    id=q.id,
                    round_no=q.round_no,
                    message=q.message,
                    released_at=q.released_at,  # type: ignore[arg-type]
                )
                for q in released
            ],
            responses=answers,
            can_respond=app.status in OPERATOR_TURN_STATES and status == ClarificationStatus.OPEN,
        )

    # Operator actions (US-065) --------------------------------------------------------------------

    def respond(
        self, operator: User, application_id: uuid.UUID, item_id: uuid.UUID, message: str
    ) -> ClarificationOperatorView:
        """Draft (or rewrite, until sent) the answer to the current open request on one item."""
        text = self._text(message)
        app = self.applications.get_for(operator, application_id, for_update=True)
        item, request = self._open_request(app, item_id)
        existing = self.checklists.responses_for_requests([request.id]).get(request.id)
        now = datetime.now(UTC)
        if existing is None:
            self.checklists.add(
                ClarificationResponse(
                    request_id=request.id, author_id=operator.id, message=text, updated_at=now
                )
            )
            self.audit.record(
                application_id=app.id,
                actor_id=operator.id,
                event_type="clarification.response_drafted",
                payload={"item_key": item.item_key, "round": request.round_no},
            )
        else:
            if existing.sent_at is not None:
                raise Conflict("This answer was sent; it can no longer change.")
            existing.message = text
            existing.updated_at = now
        self.db.commit()
        return self.build(app)

    def attach(
        self,
        operator: User,
        application_id: uuid.UUID,
        response_id: uuid.UUID,
        filename: str,
        content_type: str | None,
        stream: BinaryIO,
    ) -> tuple[ClarificationOperatorView, bool]:
        """A file on a drafted answer: the document rules, three per answer, an identical file is
        no change."""
        settings = get_settings()
        try:
            ext = check_name_and_type(filename, content_type)
        except UploadRejected as exc:
            raise BadRequest(exc.message, details={"reason": exc.reason}) from exc
        app = self.applications.get_for(operator, application_id, for_update=True)
        response = self._own_response(app, response_id)
        if response.sent_at is not None:
            raise Conflict("This answer was sent; files can no longer be added.")
        existing = self.checklists.attachments_for_responses([response.id]).get(response.id, [])
        if len(existing) >= ATTACHMENT_CAP:
            raise ValidationFailed(
                f"Up to {ATTACHMENT_CAP} files per answer.", details={"reason": "attachment_cap"}
            )
        key = new_storage_key(app.id, ext)
        digest = hashlib.sha256()
        size = 0
        limit = settings.upload_max_bytes

        def chunks() -> Iterator[bytes]:
            nonlocal size
            first = True
            while chunk := stream.read(CHUNK):
                if first:
                    try:
                        check_magic_bytes(ext, chunk[:16])
                    except UploadRejected as exc:
                        raise BadRequest(exc.message, details={"reason": exc.reason}) from exc
                    first = False
                size += len(chunk)
                if size > limit:
                    raise BadRequest(too_large_message(limit), details={"reason": "too_large"})
                digest.update(chunk)
                yield chunk
            if first:
                raise BadRequest("The file is empty.", details={"reason": "empty"})

        try:
            self.storage.put(key, chunks())
        except BadRequest:
            self.storage.delete(key)
            raise
        sha = digest.hexdigest()
        if any(a.sha256 == sha for a in existing):
            self.storage.delete(key)
            self.db.rollback()
            return self.build(self.applications.get_for(operator, application_id)), True
        row = ClarificationAttachment(
            response_id=response.id,
            original_filename=_display_name(filename),
            stored_key=key,
            content_type=canonical_content_type(ext),
            size_bytes=size,
            sha256=sha,
            uploaded_by=operator.id,
            uploaded_at=datetime.now(UTC),
        )
        self.checklists.add(row)
        self.audit.record(
            application_id=app.id,
            actor_id=operator.id,
            event_type="clarification.attachment_added",
            payload={"response_id": str(response.id), "filename": row.original_filename, "sha256": sha[:12]},
        )
        try:
            self.db.commit()
        except Exception:
            self.storage.delete(key)
            raise
        return self.build(app), False

    def remove_attachment(
        self, operator: User, application_id: uuid.UUID, response_id: uuid.UUID, attachment_id: uuid.UUID
    ) -> ClarificationOperatorView:
        app = self.applications.get_for(operator, application_id, for_update=True)
        response = self._own_response(app, response_id)
        if response.sent_at is not None:
            raise Conflict("This answer was sent; files can no longer be removed.")
        row = self.checklists.attachment(attachment_id)
        if row is None or row.response_id != response.id:
            raise NotFound("Attachment not found.")
        key = row.stored_key
        self.checklists.delete(row)
        self.audit.record(
            application_id=app.id,
            actor_id=operator.id,
            event_type="clarification.attachment_removed",
            payload={"response_id": str(response.id), "filename": row.original_filename},
        )
        self.db.commit()
        self.storage.delete(key)
        return self.build(app)

    def send(self, operator: User, application_id: uuid.UUID) -> ClarificationOperatorView:
        """Send every drafted answer of the round: each open item must carry one (422 listing the
        unanswered keys); items withdrawn before the send are left out; the case moves to Post-Site
        Clarification Resubmitted and every active officer is told."""
        from app.services.workflow import WorkflowService  # noqa: PLC0415 - the services call each other

        app = self.applications.get_for(operator, application_id, for_update=True)
        if app.status not in OPERATOR_TURN_STATES:
            raise Conflict("Your answers can be sent while the licensing office is waiting for them.")
        checklist = self.checklists.current_for(app.id)
        if checklist is None:
            raise NotFound("Nothing needs your response.")
        items = self.checklists.items_for(checklist.id)
        requests = self.checklists.requests_for_items([i.id for i in items])
        responses = self.checklists.responses_for_requests([q.id for q in requests])
        open_items = [i for i in items if i.clarification_status == ClarificationStatus.OPEN]
        if not open_items:
            raise Conflict("Nothing needs your response.")
        unanswered: list[str] = []
        to_send: list[tuple[ChecklistItem, ClarificationRequest, ClarificationResponse]] = []
        for item in open_items:
            released = [
                q
                for q in requests
                if q.item_id == item.id and q.released_at is not None and q.withdrawn_at is None
            ]
            if not released:
                continue
            latest = released[-1]
            r = responses.get(latest.id)
            if r is None or not r.message.strip():
                unanswered.append(item.item_key)
            else:
                to_send.append((item, latest, r))
        if unanswered:
            word = "item still needs" if len(unanswered) == 1 else "items still need"
            raise ValidationFailed(f"{len(unanswered)} {word} an answer.", details={"items": unanswered})
        now = datetime.now(UTC)
        for item, request, r in to_send:
            r.sent_at = now
            item.clarification_status = ClarificationStatus.ANSWERED
            self.audit.record(
                application_id=app.id,
                actor_id=operator.id,
                event_type="clarification.answered",
                payload={"item_key": item.item_key, "round": request.round_no},
            )
        self.db.flush()
        WorkflowService(self.db).apply(
            app,
            ApplicationStatus.POST_SITE_CLARIFICATION_RESUBMITTED,
            operator,
            note=None,
            actor=Actor.OPERATOR,
        )
        n = len(to_send)
        self.notifications.notify_officers(
            app,
            NotificationKind.RESUBMITTED,
            f"{app.reference_no}: The operator answered the clarification request",
            f"{operator.full_name} answered {n} {'item' if n == 1 else 'items'} after the site visit. "
            "Open the case to review the answers.",
        )
        self.db.commit()
        self.notifications.flush_sent()
        return self.build(app)

    def open_attachment(
        self, user: User, application_id: uuid.UUID, attachment_id: uuid.UUID
    ) -> tuple[ClarificationAttachment, Iterator[bytes]]:
        """The file, for the owner, an officer or an admin; the chain attachment, response, request,
        item, checklist, application is checked at every hop and an id from elsewhere is 404."""
        app = self.applications.get_for(user, application_id)
        row = self.checklists.attachment(attachment_id)
        if row is None:
            raise NotFound("Attachment not found.")
        response = self.checklists.response(row.response_id)
        request = self.checklists.request(response.request_id) if response else None
        item = self.checklists.item(request.item_id) if request else None
        checklist = self.checklists.checklist(item.checklist_id) if item else None
        if checklist is None or checklist.application_id != app.id:
            raise NotFound("Attachment not found.")
        if not self.storage.exists(row.stored_key):
            raise NotFound("The file is no longer available.")
        return row, self.storage.open(row.stored_key)

    # Helpers -------------------------------------------------------------------------------------

    @staticmethod
    def _text(message: str) -> str:
        text = (message or "").strip()
        if not text:
            raise ValidationFailed(
                "Some fields need attention.", details={"fields": {"message": "Write your answer."}}
            )
        if len(text) > MAX_MESSAGE:
            raise ValidationFailed(
                "Some fields need attention.",
                details={"fields": {"message": f"Keep it under {MAX_MESSAGE} characters."}},
            )
        return text

    def _open_request(
        self, app: Application, item_id: uuid.UUID
    ) -> tuple[ChecklistItem, ClarificationRequest]:
        if app.status not in OPERATOR_TURN_STATES:
            raise Conflict("The licensing office is not waiting for your answers right now.")
        item = self.checklists.item(item_id)
        checklist = self.checklists.checklist(item.checklist_id) if item else None
        if item is None or checklist is None or checklist.application_id != app.id:
            raise NotFound("Item not found.")
        if item.clarification_status != ClarificationStatus.OPEN:
            raise Conflict("This item is not waiting for your response.")
        released = [
            q
            for q in self.checklists.requests_for_items([item.id])
            if q.released_at is not None and q.withdrawn_at is None
        ]
        if not released:
            raise NotFound("Item not found.")
        return item, released[-1]

    def _own_response(self, app: Application, response_id: uuid.UUID) -> ClarificationResponse:
        response = self.checklists.response(response_id)
        request = self.checklists.request(response.request_id) if response else None
        item = self.checklists.item(request.item_id) if request else None
        checklist = self.checklists.checklist(item.checklist_id) if item else None
        if response is None or item is None or checklist is None or checklist.application_id != app.id:
            raise NotFound("Answer not found.")
        if app.status not in OPERATOR_TURN_STATES:
            raise Conflict("The licensing office is not waiting for your answers right now.")
        if item.clarification_status != ClarificationStatus.OPEN:
            # Withdrawn or already decided: the answer's evidence is frozen with its text.
            raise Conflict("This item is not waiting for your response.")
        return response

    # Officer side (US-066) -----------------------------------------------------------------------

    OFFICER_TURN_STATES = (
        ApplicationStatus.POST_SITE_CLARIFICATION_RESUBMITTED,
        ApplicationStatus.AWAITING_POST_SITE_CLARIFICATION,
    )

    def officer_view(self, app: Application) -> ClarificationOfficerView | None:
        """Every thread of the current visit's submitted checklist: the item's own finding on top, every
        request and answer, and what the officer may do with it now. None before the checklist is
        submitted."""
        from app.domain.enums import ChecklistStatus  # noqa: PLC0415

        checklist = self.checklists.current_for(app.id)
        if checklist is None or checklist.status != ChecklistStatus.SUBMITTED:
            return None
        items = self.checklists.items_for(checklist.id)
        requests = self.checklists.requests_for_items([i.id for i in items])
        responses = self.checklists.responses_for_requests([q.id for q in requests])
        attachments = self.checklists.attachments_for_responses([r.id for r in responses.values()])
        by_item: dict[uuid.UUID, list[ClarificationRequest]] = {}
        for q in requests:
            by_item.setdefault(q.item_id, []).append(q)
        threads: list[ClarificationThreadOut] = []
        for item in items:
            rounds = by_item.get(item.id, [])
            if not rounds:
                continue
            threads.append(self._thread_out(app, item, rounds, responses, attachments))
        counts = {
            s: sum(1 for t in threads if t.status == s) for s in ("open", "answered", "resolved", "withdrawn")
        }
        unreleased = sum(1 for t in threads if t.pending_release)
        round_no = max((t.round_no for t in threads), default=0)
        if app.status == ApplicationStatus.POST_SITE_CLARIFICATION_RESUBMITTED:
            turn = f"Round {round_no}, your turn"
        elif app.status in OPERATOR_TURN_STATES:
            turn = f"Round {round_no}, waiting on operator"
        else:
            turn = f"Round {round_no}"
        return ClarificationOfficerView(
            visit_no=checklist.visit_no,
            round=round_no,
            open_count=counts["open"],
            answered_count=counts["answered"],
            resolved_count=counts["resolved"],
            withdrawn_count=counts["withdrawn"],
            unreleased_count=unreleased,
            turn=turn,
            items=threads,
        )

    def resolve(self, officer: User, application_id: uuid.UUID, item_id: uuid.UUID) -> None:
        """Mark clarified: an answered item is done with (US-066)."""
        app = self.applications.get_for(officer, application_id, for_update=True)
        item = self._item_for(app, item_id)
        if app.status != ApplicationStatus.POST_SITE_CLARIFICATION_RESUBMITTED:
            raise Conflict("Items are decided once the operator has sent their answers.")
        if item.clarification_status != ClarificationStatus.ANSWERED:
            raise Conflict("Only an answered item can be marked clarified.")
        now = datetime.now(UTC)
        item.clarification_status = ClarificationStatus.RESOLVED
        item.resolved_by_id = officer.id
        item.resolved_at = now
        self.audit.record(
            application_id=app.id,
            actor_id=officer.id,
            event_type="clarification.resolved",
            payload={"item_key": item.item_key},
        )
        self.db.commit()

    def reopen(self, officer: User, application_id: uuid.UUID, item_id: uuid.UUID, message: str) -> None:
        """Still needs clarification: a new question for the next round, unreleased until Request
        another round; the item is open again."""
        text = self._text(message)
        app = self.applications.get_for(officer, application_id, for_update=True)
        item = self._item_for(app, item_id)
        if app.status != ApplicationStatus.POST_SITE_CLARIFICATION_RESUBMITTED:
            raise Conflict("Items are decided once the operator has sent their answers.")
        if item.clarification_status != ClarificationStatus.ANSWERED:
            raise Conflict("Only an answered item can be asked about again.")
        rounds = self.checklists.requests_for_items([item.id])
        next_round = max((q.round_no for q in rounds), default=0) + 1
        self.checklists.add(
            ClarificationRequest(item_id=item.id, round_no=next_round, author_id=officer.id, message=text)
        )
        item.clarification_status = ClarificationStatus.OPEN
        self.audit.record(
            application_id=app.id,
            actor_id=officer.id,
            event_type="clarification.reopened",
            payload={"item_key": item.item_key, "round": next_round},
        )
        self.db.commit()

    def withdraw(self, officer: User, application_id: uuid.UUID, item_id: uuid.UUID) -> None:
        """Withdraw an open question: the operator need not answer it; an unreleased draft is dropped."""
        app = self.applications.get_for(officer, application_id, for_update=True)
        item = self._item_for(app, item_id)
        if app.status not in self.OFFICER_TURN_STATES + (ApplicationStatus.PENDING_POST_SITE_RESUBMISSION,):
            raise Conflict("Questions can be withdrawn while the clarification rounds are running.")
        if item.clarification_status != ClarificationStatus.OPEN:
            raise Conflict("Only an open question can be withdrawn.")
        rounds = self.checklists.requests_for_items([item.id])
        latest = rounds[-1]
        now = datetime.now(UTC)
        latest.withdrawn_at = now
        item.clarification_status = ClarificationStatus.WITHDRAWN
        self.audit.record(
            application_id=app.id,
            actor_id=officer.id,
            event_type="clarification.withdrawn",
            payload={"item_key": item.item_key, "round": latest.round_no},
        )
        self.db.commit()

    def release_next_round(self, app: Application, officer: User, now: datetime) -> int:
        """Called by the workflow inside the Request another round transition: every unreleased
        request of the current checklist is released and audited; returns how many."""
        checklist = self.checklists.current_for(app.id)
        if checklist is None:
            return 0
        items = {i.id: i for i in self.checklists.items_for(checklist.id)}
        released = 0
        for q in self.checklists.requests_for_items(list(items)):
            if q.released_at is None and q.withdrawn_at is None:
                q.released_at = now
                released += 1
                self.audit.record(
                    application_id=app.id,
                    actor_id=officer.id,
                    event_type="clarification.released",
                    payload={"item_key": items[q.item_id].item_key, "round": q.round_no},
                )
        return released

    def _item_for(self, app: Application, item_id: uuid.UUID) -> ChecklistItem:
        item = self.checklists.item(item_id)
        checklist = self.checklists.checklist(item.checklist_id) if item else None
        if item is None or checklist is None or checklist.application_id != app.id:
            raise NotFound("Item not found.")
        return item

    def _thread_out(
        self,
        app: Application,
        item: ChecklistItem,
        rounds: list[ClarificationRequest],
        responses: dict[uuid.UUID, ClarificationResponse],
        attachments: dict[uuid.UUID, list[ClarificationAttachment]],
    ) -> ClarificationThreadOut:
        parent = ITEM_BY_KEY.get(item.parent_key or "")
        title = item_title(item.item_key, item.custom_title)
        if item.is_extra and parent is not None:
            title = f"{parent.title}: {title}"
        status = item.clarification_status
        deciding = app.status == ApplicationStatus.POST_SITE_CLARIFICATION_RESUBMITTED
        withdrawable = app.status in self.OFFICER_TURN_STATES + (
            ApplicationStatus.PENDING_POST_SITE_RESUBMISSION,
        )
        out: list[ClarificationThreadRequestOut] = []
        for q in rounds:
            r = responses.get(q.id)
            author = self.users_name(q.author_id)
            out.append(
                ClarificationThreadRequestOut(
                    id=q.id,
                    round_no=q.round_no,
                    message=q.message,
                    author_name=author,
                    created_at=q.created_at,
                    released_at=q.released_at,
                    withdrawn_at=q.withdrawn_at,
                    response=(
                        ClarificationResponseOut(
                            id=r.id,
                            round_no=q.round_no,
                            message=r.message,
                            created_at=r.created_at,
                            sent_at=r.sent_at,
                            attachments=[
                                ClarificationAttachmentOut(
                                    id=a.id,
                                    original_filename=a.original_filename,
                                    content_type=a.content_type,
                                    size_bytes=a.size_bytes,
                                    uploaded_at=a.uploaded_at,
                                )
                                for a in attachments.get(r.id, [])
                            ],
                        )
                        if r is not None and r.sent_at is not None
                        else None
                    ),
                )
            )
        return ClarificationThreadOut(
            item_id=item.id,
            key=item.item_key,
            title=title,
            result=item.result.value,
            comment=item.comment,
            status=status.value,
            round_no=max(q.round_no for q in rounds),
            requests=out,
            can_resolve=deciding and status == ClarificationStatus.ANSWERED,
            can_reopen=deciding and status == ClarificationStatus.ANSWERED,
            can_withdraw=withdrawable and status == ClarificationStatus.OPEN,
            pending_release=any(q.released_at is None and q.withdrawn_at is None for q in rounds),
        )

    def users_name(self, user_id: uuid.UUID) -> str:
        from app.repositories.users import UserRepository  # noqa: PLC0415

        user = UserRepository(self.db).get(user_id)
        return user.full_name if user else ""
