"""Cleaning for every free-text value the server stores (US-108).

Pure and deterministic. The frontend carries a mirror in `frontend/src/lib/cleanText.ts`; both are
exercised by the same fixture (`backend/tests/fixtures/form_rules.json`).
"""

import re
import unicodedata

# Zero-width (U+200B to U+200D, U+2060, U+FEFF), bidi controls (U+202A to U+202E, U+2066 to U+2069) and the
# Unicode Tag block (U+E0000 to U+E007F): invisible to a reader, readable by a model or a spoofed filename.
# Public since US-102: `ai_input` reuses it to find and strip the same characters before the AI check.
HIDDEN_CHARS = re.compile("[\u200b-\u200d\u2060\ufeff\u202a-\u202e\u2066-\u2069\U000e0000-\U000e007f]")
_CONTROL = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")
_SPACES = re.compile(r"[^\S\n]+")
_LINE_EDGES = re.compile(r" ?\n ?")
_BLANK_RUNS = re.compile(r"\n{3,}")


def clean_text(value: str, *, multiline: bool = False) -> str:
    """NFC, hidden and control characters removed, every run of spaces collapsed to one, trimmed.

    Tabs and other Unicode spaces count as spaces. With `multiline` line breaks survive (as \\n, never more
    than one blank line in a row); otherwise they are spaces too.
    """
    text = unicodedata.normalize("NFC", value)
    text = HIDDEN_CHARS.sub("", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\u2028", "\n").replace("\u2029", "\n")
    text = _CONTROL.sub("", text)
    if not multiline:
        text = text.replace("\n", " ")
    text = _SPACES.sub(" ", text)
    if multiline:
        text = _LINE_EDGES.sub("\n", text)
        text = _BLANK_RUNS.sub("\n\n", text)
    return text.strip()
