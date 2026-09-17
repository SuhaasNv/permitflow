"""Text extraction with hard caps (AI-001, ADR-004). Runs inside the background task, never the request."""

import io
import time
from dataclasses import dataclass


@dataclass(frozen=True)
class Extracted:
    text: str
    reason: str | None  # set when nothing usable could be extracted


def extract_text(
    content_type: str, data: bytes, *, max_chars: int, max_pages: int = 30, budget_seconds: float = 10.0
) -> Extracted:
    if content_type == "text/plain":
        try:
            text = data.decode("utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            return Extracted("", "undecodable_text")
        return _finish(text, max_chars)
    if content_type == "application/pdf":
        try:
            from pypdf import PdfReader

            reader = PdfReader(io.BytesIO(data))
            if reader.is_encrypted:
                return Extracted("", "encrypted_pdf")
            parts: list[str] = []
            started = time.monotonic()
            for i, page in enumerate(reader.pages):
                if i >= max_pages or time.monotonic() - started > budget_seconds:
                    break
                parts.append(page.extract_text() or "")
                if sum(len(p) for p in parts) >= max_chars:
                    break
            return _finish("\n".join(parts), max_chars)
        except Exception:  # noqa: BLE001 - a broken PDF is "unreadable", not a crash
            return Extracted("", "pdf_parse_error")
    if content_type.startswith("image/"):
        return Extracted("", "image_not_supported")
    return Extracted("", "unsupported_type")


def _finish(text: str, max_chars: int) -> Extracted:
    cleaned = text.strip()
    if not cleaned:
        return Extracted("", "no_text")
    return Extracted(cleaned[:max_chars], None)
