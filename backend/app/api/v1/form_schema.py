from typing import Any

from fastapi import APIRouter

from app.api.deps import CurrentUser
from app.domain.form_schema import schema_as_dict

router = APIRouter()


@router.get("/form-schema")
def form_schema(_: CurrentUser) -> dict[str, Any]:
    return schema_as_dict()
