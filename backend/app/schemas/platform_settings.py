"""Platform settings (US-101): the administrator's list, change, history and revert."""

import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints

SettingValue = int | bool | str

Reason = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=280)]
# Capped well under any hash input limit; the step-up re-verifies the signed-in administrator's password.
Password = Annotated[str, Field(min_length=1, max_length=200)]


class SettingOut(BaseModel):
    key: str
    label: str
    description: str
    group: str  # traffic | ai | uploads | system
    kind: str  # int | bool | choice
    unit: str
    value: SettingValue  # in force right now
    default: SettingValue  # what applies with no override: the environment value
    overridden: bool
    minimum: int | None
    maximum: int | None
    max_source: str  # env | cap | none
    choices: list[str]
    in_use: bool  # false while the consumer is a later story
    updated_by_name: str | None
    updated_at: datetime | None
    reason: str | None


class SettingsOut(BaseModel):
    settings: list[SettingOut]
    environment: str


class SettingChangeIn(BaseModel):
    value: SettingValue
    reason: Reason
    password: Password


class SettingRevertIn(BaseModel):
    reason: Reason
    password: Password


class SettingHistoryEntryOut(BaseModel):
    id: uuid.UUID
    kind: str  # changed | reverted
    key: str
    label: str
    old: SettingValue
    new: SettingValue
    old_was_default: bool
    reason: str
    actor_name: str | None
    created_at: datetime
    reverted_event_id: uuid.UUID | None


class SettingsHistoryOut(BaseModel):
    entries: list[SettingHistoryEntryOut]
    next_cursor: str | None
