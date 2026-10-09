"""PDF text extraction in a child process (US-098, ADR-016). Started by `extraction.py`, never imported by it.

Reads the PDF from stdin, prints one JSON object on stdout. The memory and CPU caps are set before pypdf
is imported, so the import and the parse both run under them. A cap that is hit kills this process
(MemoryError, SIGXCPU), which the parent reads as an unreadable PDF. Stdlib and pypdf only: it must not
import `app`, so it starts fast and carries none of the application's state.
"""

import io
import json
import resource
import sys
import time


def _cap(limit: int, value: int) -> None:
    try:
        resource.setrlimit(limit, (value, value))
    except (ValueError, OSError):
        pass  # the platform refuses the cap (macOS has no usable RLIMIT_AS); the wall clock still holds


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
    started = time.monotonic()
    for i, page in enumerate(reader.pages):
        if i >= max_pages or time.monotonic() - started > budget_seconds:
            break
        parts.append(page.extract_text() or "")
        if sum(len(p) for p in parts) >= max_chars:
            break
    print(json.dumps({"encrypted": False, "text": "\n".join(parts)}))


if __name__ == "__main__":
    main()
