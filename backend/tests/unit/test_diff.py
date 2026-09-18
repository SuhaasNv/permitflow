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
