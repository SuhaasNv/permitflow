"""Hardening of everything that goes to the AI document check (US-102, SEC-008, T18). Pure Python.

Three steps run before the injection check and before any text reaches a provider:

1. Clean. Hidden characters (zero-width, bidirectional overrides and isolates, the Unicode Tag block) are
   stripped, the text is normalised with NFKC (fullwidth and mathematical letters become plain ones), and
   the shared cleaner from US-108 (`text_clean`) tidies spaces and control characters.
2. Detect. Finding hidden characters at all raises `possible_prompt_injection`, with the hidden text
   decoded for the evidence (Tag-block characters are ASCII in disguise). The phrase heuristic then runs
   on a "skeleton" of the text, where look-alike letters from other scripts are folded to Latin (Unicode
   TR39 confusables) and accents are dropped, and on the decoded hidden text too. The skeleton is for the
   detector only: the provider receives the cleaned text, not the folded one.
3. Redact. NRIC/FIN numbers (with a valid checksum letter) and Singapore phone numbers are masked, keeping
   the last 4 characters. The same masking is applied to the form values sent beside the text, so a number
   in the document and the same number on the form still read identically to the model.

A few hidden characters are ordinary writing and are not flagged: a byte-order mark at the very start, a
joiner inside an emoji sequence or between letters of a joining script (Tamil, Devanagari, Arabic and the
like), and the Tag-block subdivision flags (England, Scotland, Wales). They are still stripped.
"""

import re
import unicodedata
from dataclasses import dataclass
from typing import Any

from app.domain.confusables_data import CONFUSABLES
from app.domain.text_clean import HIDDEN_CHARS, clean_text
from app.domain.verification_rules import find_injection_phrases

_TAG_BASE = 0xE0000
# Invisible in print but not an instruction channel: stripped without raising a flag (soft hyphen from PDF
# line breaks, combining grapheme joiner, Arabic letter mark, Mongolian vowel separator, invisible operators).
_QUIET_CHARS = re.compile("[\u00ad\u034f\u061c\u180e\u2062-\u2064]")
# U+1F3F4 (black flag) + tag letters + cancel tag: how the flags of England, Scotland and Wales are written.
_FLAG_SEQUENCE = re.compile("\U0001f3f4([\U000e0020-\U000e007e]+)\U000e007f")
_FLAG_CODE = re.compile(r"[a-z0-9]{2,7}")
_JOINING_SCRIPTS = frozenset(
    {
        "TAMIL",
        "DEVANAGARI",
        "BENGALI",
        "GURMUKHI",
        "GUJARATI",
        "ORIYA",
        "TELUGU",
        "KANNADA",
        "MALAYALAM",
        "SINHALA",
        "ARABIC",
        "MYANMAR",
        "KHMER",
    }
)
_WHITESPACE = re.compile(r"\s+")
_EVIDENCE_MAX = 200


@dataclass(frozen=True)
class PreparedText:
    text: str  # what the provider receives: cleaned, redacted
    injection: list[str]  # evidence for `apply_rules`; empty when nothing suspicious was found
    hidden_count: int  # hidden characters that raised the flag
    redactions: int  # numbers masked


def prepare_text(raw: str) -> PreparedText:
    """Clean, check and redact one document's extracted text."""
    unflagged = _without_ordinary_flags(raw)
    suspicious = _suspicious_hidden(unflagged)
    decoded = _decode_tags(unflagged).strip()

    stripped = _QUIET_CHARS.sub("", HIDDEN_CHARS.sub("", raw))
    cleaned = clean_text(unicodedata.normalize("NFKC", stripped), multiline=True)

    signals: list[str] = []
    if decoded:
        signals.append(f"hidden text: {decoded[:_EVIDENCE_MAX]}")
    elif suspicious:
        signals.append(f"hidden characters ({len(suspicious)})")
    signals += find_injection_phrases(skeleton(cleaned))

    text, redactions = redact(cleaned)
    return PreparedText(text=text, injection=signals, hidden_count=len(suspicious), redactions=redactions)


def skeleton(text: str) -> str:
    """The text as a detector should read it: accents dropped, look-alike letters folded to Latin, runs of
    white space (including line breaks) collapsed to one space."""
    decomposed = unicodedata.normalize("NFD", text)
    bare = "".join(c for c in decomposed if unicodedata.category(c) != "Mn")
    return _WHITESPACE.sub(" ", bare.translate(CONFUSABLES))


# ---------- hidden characters ----------


def _decode_tags(text: str) -> str:
    """Tag-block characters are ASCII shifted to U+E0000: the hidden message, readable by a model."""
    return "".join(chr(ord(c) - _TAG_BASE) for c in text if 0xE0020 <= ord(c) <= 0xE007E)


def _without_ordinary_flags(text: str) -> str:
    def keep_if_not_a_flag(match: re.Match[str]) -> str:
        return "" if _FLAG_CODE.fullmatch(_decode_tags(match.group(1))) else match.group(0)

    return _FLAG_SEQUENCE.sub(keep_if_not_a_flag, text)


def _suspicious_hidden(text: str) -> list[str]:
    found: list[str] = []
    for match in HIDDEN_CHARS.finditer(text):
        char, index = match.group(), match.start()
        if char == "\ufeff" and index == 0:
            continue
        if char in "\u200c\u200d" and _is_joiner_in_writing(text, index):
            continue
        found.append(char)
    return found


def _is_joiner_in_writing(text: str, index: int) -> bool:
    if index == 0 or index + 1 >= len(text):
        return False
    before, after = text[index - 1], text[index + 1]
    if text[index] == "\u200d" and _is_emoji(before) and _is_emoji(after):
        return True
    return _script(before) in _JOINING_SCRIPTS and _script(after) in _JOINING_SCRIPTS


def _script(char: str) -> str:
    return unicodedata.name(char, "").split(" ", 1)[0]


def _is_emoji(char: str) -> bool:
    code = ord(char)
    return (
        0x1F000 <= code <= 0x1FAFF
        or 0x2190 <= code <= 0x21FF
        or 0x2300 <= code <= 0x23FF
        or 0x2600 <= code <= 0x27BF
        or 0x2B00 <= code <= 0x2BFF
        or code == 0xFE0F
    )


# ---------- redaction ----------

_NRIC = re.compile(r"(?<![A-Za-z0-9])[STFGMstfgm]\d{7}[A-Za-z](?![A-Za-z0-9])")
_NRIC_WEIGHTS = (2, 7, 6, 5, 4, 3, 2)
_NRIC_ST = "JZIHGFEDCBA"
_NRIC_FG = "XWUTRQPNMLK"
_NRIC_M = "KLJNPQRTUWX"
# Singapore numbers: 8 digits starting 3, 6, 8 or 9, with or without +65 / 65 / 0065 and a space or hyphen.
_PHONE = re.compile(r"(?<![A-Za-z0-9])(?:(?:\+|00)?65[ -]?)?([3689]\d{3})[ -]?(\d{4})(?![A-Za-z0-9])")
_DDMMYYYY = re.compile(r"3[01](?:0[1-9]|1[0-2])(?:19|20)\d{2}")
_KEPT = 4


def redact(text: str) -> tuple[str, int]:
    """Mask NRIC/FIN and Singapore phone numbers, keeping the last 4 characters. Returns the text and how
    many numbers were masked."""
    count = 0

    def mask_nric(match: re.Match[str]) -> str:
        nonlocal count
        value = match.group()
        if not _nric_checksum_ok(value):
            return value
        count += 1
        return "*" * (len(value) - _KEPT) + value[-_KEPT:]

    def mask_phone(match: re.Match[str]) -> str:
        nonlocal count
        whole = match.group()
        # Eight bare digits starting with 3 can be a date written without separators (31102027).
        if whole.isdigit() and _DDMMYYYY.fullmatch(whole):
            return whole
        count += 1
        return "****" + match.group(2)

    return _PHONE.sub(mask_phone, _NRIC.sub(mask_nric, text)), count


def redact_form_section(section: dict[str, Any]) -> dict[str, Any]:
    """The form values sent beside the document, masked the same way, so a masked number in the text and
    the same number in the form compare equal."""
    return {key: _redact_value(value) for key, value in section.items()}


def _redact_value(value: Any) -> Any:
    if isinstance(value, str):
        return redact(value)[0]
    if isinstance(value, dict):
        return {k: _redact_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_redact_value(v) for v in value]
    return value


def _nric_checksum_ok(value: str) -> bool:
    prefix, digits, check = value[0].upper(), value[1:8], value[8].upper()
    if prefix == "M":
        # The M series (from 2022) has its own letter table; the shape and the letter set are enough here,
        # and masking one number too many is the safe direction.
        return check in _NRIC_M
    total = sum(int(d) * w for d, w in zip(digits, _NRIC_WEIGHTS, strict=True))
    if prefix in "TG":
        total += 4
    table = _NRIC_ST if prefix in "ST" else _NRIC_FG
    return table[total % 11] == check
