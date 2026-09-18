"""US-051: licence data and rendering are pure and readable back."""

from datetime import date
from io import BytesIO

from pypdf import PdfReader

from app.domain.licence import build_licence_data, licence_number, validity, verification_code
from app.infra.pdf.licence import render_licence_pdf

FORM = {
    "business": {
        "business_name": "Kopi & Kaya Toast House Pte. Ltd.",
        "uen": "202355555E",
        "entity_type": "private_limited",
    },
    "premises": {"address_line_1": "10 Jalan Besar #01-12", "postal_code": "208787"},
}


def test_number_validity_and_code_are_deterministic() -> None:
    assert licence_number(2026, 7) == "FEL-2026-000007"
    assert validity(date(2026, 9, 19)) == (date(2026, 9, 19), date(2027, 9, 18))
    a = verification_code("FEL-2026-000007", "PF-2026-001005", date(2026, 9, 19))
    b = verification_code("FEL-2026-000007", "PF-2026-001005", date(2026, 9, 19))
    assert a == b and len(a) == 14 and a.count("-") == 2
    assert a != verification_code("FEL-2026-000008", "PF-2026-001005", date(2026, 9, 19))


def test_pdf_carries_every_fact_as_text() -> None:
    data = build_licence_data(
        licence_no="FEL-2026-000007",
        reference_no="PF-2026-001005",
        form_data=FORM,
        holder_name="Tan Wei Ling",
        approved_by="Rahim bin Abdullah",
        issued_on=date(2026, 9, 19),
    )
    pdf = render_licence_pdf(data)
    assert pdf.startswith(b"%PDF")
    text = PdfReader(BytesIO(pdf)).pages[0].extract_text()
    for needle in (
        "Food Establishment Licence",
        "FEL-2026-000007",
        "PF-2026-001005",
        "Kopi & Kaya Toast House Pte. Ltd.",
        "202355555E",
        "10 Jalan Besar #01-12",
        "Tan Wei Ling",
        "18 September 2027",
        "Rahim bin Abdullah",
        data.verification_code,
        "Fictional document",
    ):
        assert needle in text, needle
    assert "PREVIEW" not in text
    preview = render_licence_pdf(
        build_licence_data(
            licence_no="FEL-2026-000000",
            reference_no="PF-2026-001005",
            form_data=FORM,
            holder_name="x",
            approved_by="y",
            issued_on=date(2026, 9, 19),
            preview=True,
        )
    )
    assert "PREVIEW" in PdfReader(BytesIO(preview)).pages[0].extract_text()


def test_render_is_deterministic_and_clips_unbreakable_text() -> None:
    long_form = {
        "business": {"business_name": "A" * 120, "uen": "202355555E", "entity_type": "private_limited"},
        "premises": {"address_line_1": "B" * 200, "postal_code": "208787"},
    }
    data = build_licence_data(
        licence_no="FEL-2026-000009",
        reference_no="PF-2026-001009",
        form_data=long_form,
        holder_name="C" * 120,
        approved_by="Officer With A Very Long Name Indeed For The Signature Strip",
        issued_on=date(2026, 9, 19),
    )
    first, second = render_licence_pdf(data), render_licence_pdf(data)
    assert first == second
    text = PdfReader(BytesIO(first)).pages[0].extract_text()
    assert "..." in text  # unbreakable values are clipped, never drawn past the frame
    assert "FEL-2026-000009" in text
