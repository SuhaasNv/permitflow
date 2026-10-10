"""The virus scan's vocabulary and the PDF active-content rule (US-099, ADR-017). Pure: no I/O.

A file's `scan_state` is NULL when it was stored with the scan off (or before it existed): served as before.
With `SCAN_MODE=enforce` it is `scanning` from the upload until the scanner answers, then `clean` or
`infected`. Only NULL and `clean` are served.
"""

import re
import uuid
from collections.abc import Iterable
from pathlib import PurePosixPath

SCANNING = "scanning"
CLEAN = "clean"
INFECTED = "infected"

QUARANTINE_PREFIX = "quarantine/"

# What the screens map to "This file was blocked by the security check. Upload a different copy."
INFECTED_CODE = "file_infected"
INFECTED_MESSAGE = "This file was blocked by the security check. Upload a different copy."
OFFICER_INFECTED_MESSAGE = "This file was blocked by the security check and cannot be opened."
SCANNING_MESSAGE = "This file is still being checked. Try again in a moment."

# The run reasons (the same vocabulary as `error_reason` on a verification run).
REASON_INFECTED = INFECTED_CODE
REASON_SCANNER_UNAVAILABLE = "scanner_unavailable"


def servable(scan_state: str | None) -> bool:
    return scan_state is None or scan_state == CLEAN


DOCUMENTS_NOT_CLEAR_MESSAGE = "Review and submit opens when no document is blocked or being scanned."


def blocked_reason(states: Iterable[str | None], lead: str = DOCUMENTS_NOT_CLEAR_MESSAGE) -> str | None:
    """The sentence the screens show when the documents' scan states stop a submission, with the counts
    ("1 blocked, 1 being scanned."); None when nothing stops it."""
    states = list(states)
    parts = [
        f"{n} {label}"
        for n, label in ((states.count(INFECTED), "blocked"), (states.count(SCANNING), "being scanned"))
        if n
    ]
    return f"{lead} {', '.join(parts)}." if parts else None


def quarantine_key(key: str) -> str:
    return QUARANTINE_PREFIX + key


def released_key(key: str) -> str:
    """A new normal key for a quarantined file (unchanged for one that was never quarantined). It is unique
    on every call, so two scans of one document never share a final key and the loser of a race deletes only
    its own copy."""
    if not key.startswith(QUARANTINE_PREFIX):
        return key
    path = PurePosixPath(key.removeprefix(QUARANTINE_PREFIX))
    return str(path.with_name(uuid.uuid4().hex + path.suffix))


_NAME_ESCAPE = re.compile(rb"#([0-9A-Fa-f]{2})")


def _name(token: bytes) -> re.Pattern[bytes]:
    # A PDF name ends at whitespace or a delimiter: `/AA` must not match `/AAPL`.
    return re.compile(rb"/" + token + rb"(?![A-Za-z0-9_.\-])")


_AUTOMATIC = (_name(b"OpenAction"), _name(b"AA"))
_SCRIPT = (_name(b"JavaScript"), _name(b"JS"))
_ALWAYS = (_name(b"Launch"), _name(b"EmbeddedFiles?"))


def pdf_active_content(data: bytes) -> bool:
    """True when the PDF can act on its own: an automatic action (`/OpenAction`, `/AA`) next to a script
    (`/JavaScript`, `/JS`), or a `/Launch` action, or an embedded file. Names written with `#xx` escapes
    are decoded first, so `/Java#53cript` does not slip past.
    ponytail: a byte scan, not a parser. Objects packed in compressed object streams are not visible to it;
    ClamAV remains the control for those. Upgrade path: walk the objects with pypdf."""
    text = _NAME_ESCAPE.sub(lambda m: bytes([int(m.group(1), 16)]), data)
    if any(p.search(text) for p in _ALWAYS):
        return True
    return any(p.search(text) for p in _AUTOMATIC) and any(p.search(text) for p in _SCRIPT)
