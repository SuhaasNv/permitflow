"""Request fields that carry free text are cleaned on the way in (US-108): NFC, hidden and control
characters removed, runs of spaces collapsed, trimmed. Length limits then apply to the cleaned text."""

from typing import Annotated, Any

from pydantic import BeforeValidator

from app.domain.text_clean import clean_text


def _line(value: Any) -> Any:
    return clean_text(value) if isinstance(value, str) else value


def _block(value: Any) -> Any:
    return clean_text(value, multiline=True) if isinstance(value, str) else value


CleanLine = Annotated[str, BeforeValidator(_line)]
CleanBlock = Annotated[str, BeforeValidator(_block)]
