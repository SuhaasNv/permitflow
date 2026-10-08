from app.domain.diff import DocumentRef, diff_documents, diff_forms
from app.domain.enums import DocumentType


def test_form_diff_is_field_level_and_schema_bound() -> None:
    before = {
        "premises": {"address_line_1": "10 Jalan Besar #01-12", "postal_code": "208787"},
        "junk": {"x": 1},
    }
    after = {
        "premises": {"address_line_1": "10 Jalan Besar #01-21", "postal_code": "208787"},
        "junk": {"x": 2},
    }
    out = {s.key: s for s in diff_forms(before, after)}
    assert out["premises"].changed and [f.key for f in out["premises"].fields] == ["address_line_1"]
    assert out["premises"].fields[0].old == "10 Jalan Besar #01-12"
    assert out["premises"].fields[0].new == "10 Jalan Besar #01-21"
    assert not out["business"].changed and out["business"].fields == []
    assert "junk" not in out


def test_form_diff_compares_the_stored_form_so_legacy_text_is_not_a_change() -> None:
    legacy = {"contact_phone": "91234567", "contact_email": "Tan@Shop.sg", "business_name": "Kopi House"}
    clean = {"contact_phone": "+65 9123 4567", "contact_email": "tan@shop.sg", "business_name": "Kopi House"}
    assert not {s.key: s for s in diff_forms({"business": legacy}, {"business": clean})}["business"].changed
    edited = {**clean, "business_name": "Kopi Two"}
    business = {s.key: s for s in diff_forms({"business": legacy}, {"business": edited})}["business"]
    assert [f.key for f in business.fields] == ["business_name"]
    # free-text hours compare as written, and a real change to them still shows
    before = {"operations": {"operating_hours": "Mon-Sun 7am-9pm"}}
    after = {"operations": {"operating_hours": "Mon-Sat 7am-9pm"}}
    assert not {s.key: s for s in diff_forms(before, before)}["operations"].changed
    assert {s.key: s for s in diff_forms(before, after)}["operations"].changed


def test_document_diff_compares_by_hash() -> None:
    a = DocumentRef("1", "aaa", "plan.pdf")
    b_same = DocumentRef("2", "aaa", "plan-copy.pdf")
    c = DocumentRef("3", "ccc", "plan-v2.pdf")
    out = {
        d.type: d
        for d in diff_documents(
            {DocumentType.FLOOR_PLAN: a, DocumentType.TENANCY_AGREEMENT: a},
            {
                DocumentType.FLOOR_PLAN: c,
                DocumentType.BUSINESS_PROFILE: b_same,
                DocumentType.TENANCY_AGREEMENT: b_same,
            },
        )
    }
    assert out[DocumentType.FLOOR_PLAN].change == "replaced"
    assert out[DocumentType.BUSINESS_PROFILE].change == "added"
    assert out[DocumentType.TENANCY_AGREEMENT].change == "unchanged"  # same bytes, new upload
    assert out[DocumentType.FOOD_HYGIENE_CERTIFICATE].change == "unchanged"
    assert out[DocumentType.FLOOR_PLAN].old is a and out[DocumentType.FLOOR_PLAN].new is c
