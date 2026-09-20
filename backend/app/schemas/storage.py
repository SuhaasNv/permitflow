"""What an application holds on the volume against its budget (US-085), shown before an upload."""

from pydantic import BaseModel


class StorageView(BaseModel):
    used_bytes: int
    budget_bytes: int
    remaining_bytes: int


__all__ = ["StorageView"]
