"""US-100: the pure rules behind the AI usage record: cost arithmetic, bounded metric labels, the keyed
pseudonyms, the Telegram line and the formula-safe CSV cell."""

import uuid
from decimal import Decimal

import pytest

from app.domain.ai_usage import (
    CSV_COLUMNS,
    DOCUMENT_TYPE_LABELS,
    OUTCOME_LABELS,
    bounded_label,
    check_message,
    cost_usd,
    csv_cell,
    pseudonym,
)
from app.domain.enums import DocumentType, VerificationStatus

IN, OUT = Decimal("0.40"), Decimal("1.60")  # gpt-4.1-mini, USD per million tokens


def test_cost_is_tokens_times_the_price_per_million() -> None:
    assert cost_usd(1_000_000, 1_000_000, IN, OUT) == Decimal("2.00000000")
    assert cost_usd(1200, 80, IN, OUT) == Decimal("0.00060800")  # 0.00048 + 0.000128
    assert cost_usd(0, 0, IN, OUT) == Decimal(0)


def test_cost_keeps_eight_decimals_and_rounds_half_up() -> None:
    # 1 token at 0.40 per million is 4e-7: well inside the column's resolution.
    assert cost_usd(1, 0, IN, OUT) == Decimal("0.00000040")
    # 0.5e-8 rounds up to 1e-8.
    assert cost_usd(1, 0, Decimal("0.005"), Decimal(0)) == Decimal("0.00000001")


def test_labels_are_the_closed_enum_vocabularies() -> None:
    assert DOCUMENT_TYPE_LABELS == {t.value for t in DocumentType}
    assert OUTCOME_LABELS == {s.value for s in VerificationStatus}
    assert bounded_label("floor_plan", DOCUMENT_TYPE_LABELS) == "floor_plan"
    assert bounded_label("verified", OUTCOME_LABELS) == "verified"


@pytest.mark.parametrize("hostile", [str(uuid.uuid4()), "ops@example.sg", "", "floor_plan; drop", "x" * 500])
def test_anything_else_collapses_to_one_label(hostile: str) -> None:
    assert bounded_label(hostile, DOCUMENT_TYPE_LABELS) == "other"
    assert bounded_label(hostile, OUTCOME_LABELS) == "other"


def test_pseudonyms_are_stable_keyed_and_do_not_contain_the_id() -> None:
    user = uuid.uuid4()
    a = pseudonym("secret-one", "user", user)
    assert a == pseudonym("secret-one", "user", user)  # same person, same stand-in
    assert a != pseudonym("secret-two", "user", user)  # the key matters
    assert a != pseudonym("secret-one", "application", user)  # a user and a case never collide
    assert a != pseudonym("secret-one", "user", uuid.uuid4())
    assert len(a) == 16 and int(a, 16) >= 0
    assert str(user) not in a and user.hex[:8] not in a


def test_the_telegram_line_has_the_check_and_no_person() -> None:
    text = check_message(
        document_type="floor_plan",
        outcome="issues_found",
        cost=Decimal("0.00060800"),
        latency_ms=3456,
        reference_no="PF-2026-000042",
    )
    assert text == "Document check: floor plan · issues found · USD 0.0006 · 3.5 s · case PF-2026-000042"
    assert "@" not in text
    assert check_message(
        document_type="tenancy_agreement",
        outcome="verified",
        cost=Decimal(0),
        latency_ms=0,
        reference_no=None,
    ).endswith("USD 0.0000 · 0.0 s")


@pytest.mark.parametrize("lead", ["=", "+", "-", "@", "\t", "\r"])
def test_csv_cells_that_start_like_a_formula_get_a_single_quote(lead: str) -> None:
    cell = f'{lead}HYPERLINK("http://evil","x")'
    assert csv_cell(cell) == "'" + cell


def test_csv_cells_that_are_safe_are_left_alone() -> None:
    assert csv_cell("Tan Wei Ming") == "Tan Wei Ming"
    assert csv_cell("a=b") == "a=b"  # only the first character matters
    assert csv_cell(None) == ""
    assert csv_cell(1200) == "1200"
    assert csv_cell(uuid.UUID(int=1)) == "00000000-0000-0000-0000-000000000001"
    assert csv_cell("'=already quoted") == "'=already quoted"


def test_the_csv_has_one_column_per_field_of_the_page() -> None:
    assert len(CSV_COLUMNS) == len(set(CSV_COLUMNS)) == 15
    assert {"user_id", "application_id", "cost_usd", "outcome", "input_tokens", "output_tokens"} <= set(
        CSV_COLUMNS
    )
