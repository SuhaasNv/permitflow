"""US-108 audit of the other forms: request free text is cleaned before it is checked or stored."""

import pytest
from pydantic import ValidationError

from app.models.enums import Role
from app.schemas.admin import UserCreateIn
from app.schemas.applications import WithdrawIn
from app.schemas.checklist import ChecklistItemIn
from app.schemas.clarification import ClarificationReopenIn, ClarificationResponseIn
from app.schemas.officer import FeedbackIn, TransitionIn
from app.schemas.site_visit import SiteVisitProposeIn

HIDDEN = "\u200b\u202e\ufeff\U000e0041"


def test_messages_lose_hidden_characters_and_keep_their_lines() -> None:
    raw = f"Please  attach{HIDDEN} the\r\nfloor plan.\n\n\n\nThanks"
    assert ClarificationResponseIn(message=raw).message == "Please attach the\nfloor plan.\n\nThanks"
    assert ClarificationReopenIn(message=raw).message == "Please attach the\nfloor plan.\n\nThanks"
    assert TransitionIn(target="rejected", expected_version=1, note=raw).note == (
        "Please attach the\nfloor plan.\n\nThanks"
    )
    assert WithdrawIn(reason=f" changed{HIDDEN} my mind ").reason == "changed my mind"


def test_feedback_and_checklist_comments_are_cleaned() -> None:
    fb = FeedbackIn.model_validate(
        {"target_type": "section", "section_key": "premises", "message": f"  Check{HIDDEN} the unit  "}
    )
    assert fb.message == "Check the unit"
    item = ChecklistItemIn.model_validate(
        {"key": "x", "result": "pass", "comment": f"ok{HIDDEN}", "custom_title": f"  Extra{HIDDEN}   item "}
    )
    assert item.comment == "ok" and item.custom_title == "Extra item"


def test_length_limits_count_the_cleaned_text() -> None:
    assert ClarificationResponseIn(message="a" * 2000 + HIDDEN).message == "a" * 2000
    with pytest.raises(ValidationError):
        ClarificationResponseIn(message="a" * 2001)


def test_site_visit_notes_are_cleaned() -> None:
    body = SiteVisitProposeIn.model_validate(
        {"date": "2026-12-01", "slot": "morning", "note": f" Bring{HIDDEN}  keys ", "expected_version": 1}
    )
    assert body.note == "Bring keys"


def test_an_account_name_cannot_be_blank_or_hidden() -> None:
    ok = UserCreateIn(
        email="a@b.sg",
        full_name=f"  Tan{HIDDEN}   Wei ",
        role=Role.OFFICER,
        password="x" * 12,
        admin_password="y",
    )
    assert ok.full_name == "Tan Wei"
    with pytest.raises(ValidationError):
        UserCreateIn(
            email="a@b.sg", full_name=f" {HIDDEN} ", role=Role.OFFICER, password="x" * 12, admin_password="y"
        )
