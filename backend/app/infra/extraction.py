"""Text extraction with hard caps (AI-001, ADR-004). Runs inside the background task, never the request.

A PDF is parsed in a child process (US-098, ADR-016): killed at a wall-clock deadline and capped in memory
and CPU time, so a hostile or pathological file costs one failed check, never the API or the worker.
"""

import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from app.core.settings import get_settings

_CHILD = Path(__file__).with_name("pdf_text_child.py")


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
        return _pdf_in_child(data, max_chars=max_chars, max_pages=max_pages, budget_seconds=budget_seconds)
    if content_type.startswith("image/"):
        return Extracted("", "image_not_supported")
    return Extracted("", "unsupported_type")


def _pdf_in_child(data: bytes, *, max_chars: int, max_pages: int, budget_seconds: float) -> Extracted:
    settings = get_settings()
    limits = [max_chars, max_pages, budget_seconds, settings.pdf_extract_memory_mb]
    command = [sys.executable, "-I", str(_CHILD), *map(str, limits), str(settings.pdf_extract_cpu_seconds)]
    try:
        # `run` kills the child when the deadline passes. Every failure is "unreadable", never a crash.
        done = subprocess.run(
            command, input=data, capture_output=True, timeout=settings.pdf_extract_timeout_seconds, check=True
        )
        out = json.loads(done.stdout)
        if out["encrypted"]:
            return Extracted("", "encrypted_pdf")
        return _finish(str(out["text"]), max_chars)
    except (subprocess.SubprocessError, OSError, ValueError, KeyError):
        return Extracted("", "pdf_parse_error")


def _finish(text: str, max_chars: int) -> Extracted:
    cleaned = text.strip()
    if not cleaned:
        return Extracted("", "no_text")
    return Extracted(cleaned[:max_chars], None)
