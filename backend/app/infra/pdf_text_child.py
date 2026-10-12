"""PDF text extraction in a child process (US-098, ADR-016). Started by `extraction.py`, never imported by it.

Reads the PDF from stdin, prints one JSON object on stdout. The memory and CPU caps are set before pypdf
is imported, so the import and the parse both run under them. A cap that is hit kills this process
(MemoryError, SIGXCPU), which the parent reads as an unreadable PDF. Stdlib and pypdf only: it must not
import `app`, so it starts fast and carries none of the application's state.
"""

import io
import json
import math
import resource
import sys
import time
from typing import Any

_MIN_PT = 3.0  # text drawn smaller than this is not meant to be read
_NEAR_WHITE = 0.95
_HIDDEN_MAX = 500  # characters of invisible text reported back


def _cap(limit: int, value: int) -> None:
    try:
        resource.setrlimit(limit, (value, value))
    except (ValueError, OSError):
        pass  # the platform refuses the cap (macOS has no usable RLIMIT_AS); the wall clock still holds


class _Hidden:
    """Tracks the fill colour and render mode through the content stream (pypdf's visitor sees operators in
    order) so each shown string can be judged: invisible (render mode 3 or 7), white or near-white fill, or
    drawn smaller than `_MIN_PT` once the text and page matrices are applied."""

    def __init__(self) -> None:
        self.mode = 0
        self.white = False
        self.stack: list[tuple[int, bool]] = []
        self.found: list[str] = []

    def operand(self, op: bytes, args: list[Any], cm: list[float], tm: list[float]) -> None:
        if op == b"q":
            self.stack.append((self.mode, self.white))
        elif op == b"Q" and self.stack:
            self.mode, self.white = self.stack.pop()
        elif op == b"Tr" and args:
            self.mode = int(args[0])
        elif op in (b"g", b"rg", b"k", b"sc", b"scn"):
            try:
                v = [float(a) for a in args]
            except (TypeError, ValueError):
                return  # a pattern name: not a plain colour
            if len(v) == 4:
                self.white = max(v) <= 1 - _NEAR_WHITE
            else:
                self.white = len(v) in (1, 3) and min(v) >= _NEAR_WHITE

    def text(self, text: str, cm: list[float], tm: list[float], font_size: float) -> None:
        if not text.strip():
            return
        scale = math.hypot(tm[0], tm[1]) * math.hypot(cm[0], cm[1])
        if self.mode in (3, 7) or self.white or font_size * scale < _MIN_PT:
            self.found.append(text.strip())


def main() -> None:
    max_chars, max_pages, budget_seconds, memory_mb, cpu_seconds = (float(a) for a in sys.argv[1:6])
    _cap(resource.RLIMIT_CPU, int(cpu_seconds))
    _cap(resource.RLIMIT_AS, int(memory_mb) * 1024 * 1024)
    data = sys.stdin.buffer.read()

    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    if reader.is_encrypted:
        print(json.dumps({"encrypted": True, "text": ""}))
        return
    parts: list[str] = []
    hidden = _Hidden()
    started = time.monotonic()
    for i, page in enumerate(reader.pages):
        if i >= max_pages or time.monotonic() - started > budget_seconds:
            break
        hidden.mode, hidden.white, hidden.stack = 0, False, []  # each page starts in the default state
        parts.append(
            page.extract_text(
                visitor_operand_before=lambda op, args, cm, tm: hidden.operand(op, args, cm, tm),
                visitor_text=lambda text, cm, tm, font, size: hidden.text(text, cm, tm, size),
            )
            or ""
        )
        if sum(len(p) for p in parts) >= max_chars:
            break
    # Never more than the cap, so the parent does not buffer a page's worth beyond it.
    out = {
        "encrypted": False,
        "text": "\n".join(parts)[: int(max_chars)],
        "hidden": " ".join(hidden.found)[:_HIDDEN_MAX],
    }
    print(json.dumps(out))


if __name__ == "__main__":
    main()
