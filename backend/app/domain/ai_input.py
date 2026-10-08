"""Hardening of everything that goes to the AI document check (US-102, SEC-008, T18). Pure Python.

Three steps run before the injection check and before any text reaches a provider:

1. Clean. Hidden characters (zero-width, bidirectional overrides and isolates, the Unicode Tag block,
   variation selectors, Hangul fillers, left-to-right and right-to-left marks) are stripped, the text is
   normalised with NFKC (fullwidth and mathematical letters become plain ones), and the shared cleaner
   from US-108 (`text_clean`) tidies spaces and control characters. A `<document>` or `</document>` tag
   inside the text is replaced by `[document]` / `[/document]`, so the text cannot close the data block
   the provider wraps it in.
2. Detect. Finding hidden characters at all raises `possible_prompt_injection`, with the hidden text
   decoded for the evidence (Tag-block characters are ASCII in disguise; variation selectors carry one
   byte each). A delimiter tag in the text raises it too. The phrase heuristic then runs on a "skeleton"
   of the text, where look-alike letters from other scripts are folded to Latin (Unicode TR39
   confusables) and accents are dropped, and on the decoded hidden text too. The skeleton is for the
   detector only: the provider receives the cleaned text, not the folded one.
3. Redact. NRIC/FIN numbers (with a valid checksum letter) and Singapore phone numbers are masked, keeping
   the last 4 characters. The same masking is applied to the form values sent beside the text (NFKC first,
   like the text), so a number in the document and the same number on the form still read identically to
   the model.

A few hidden characters are ordinary writing and are not flagged: a byte-order mark at the very start, a
joiner inside an emoji sequence or between letters of a joining script (Tamil, Devanagari, Arabic and the
like), a single zero-width space between letters of Thai, Lao or Khmer (word breaking), a variation
selector directly after an emoji, and the three Tag-block subdivision flags (England, Scotland, Wales).
They are still stripped, except the emoji selector.
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
# Other hidden or invisible characters that carry a message or break a word for a reader but not for a
# model: variation selectors (U+FE00 to U+FE0F, U+E0100 to U+E01EF: 256 values, one byte each), Hangul
# fillers (U+115F, U+1160, U+3164, U+FFA0) and the left-to-right / right-to-left marks (U+200E, U+200F).
# Not in `text_clean.HIDDEN_CHARS`, which the typed-text cleaner shares with the frontend.
_SMUGGLING = "[\ufe00-\ufe0f\U000e0100-\U000e01ef\u115f\u1160\u3164\uffa0\u200e\u200f]"
_ALL_HIDDEN = re.compile(f"{HIDDEN_CHARS.pattern}|{_SMUGGLING}")
_SELECTOR_RUN = re.compile("[\ufe00-\ufe0f\U000e0100-\U000e01ef]{2,}")
# U+1F3F4 (black flag) + tag letters + cancel tag: the only three flags that are written this way (England,
# Scotland, Wales). Any other tag run after a black flag is hidden text.
_BLACK_FLAG = "\U0001f3f4"
_FLAG_SEQUENCE = re.compile(
    _BLACK_FLAG
    + "(?:"
    + "|".join("".join(chr(_TAG_BASE + ord(c)) for c in code) for code in ("gbeng", "gbsct", "gbwls"))
    + ")\U000e007f"
)
# Characters an emoji presentation selector (U+FE0F) can follow besides the pictographs in `_is_emoji`:
# copyright and trade mark signs and a few symbols. Keycap bases (# * 0 to 9) count only before U+20E3.
_SELECTOR_BASES = frozenset(
    "\u00a9\u00ae\u203c\u2049\u2122\u2139\u24c2\u25aa\u25ab\u25b6\u25c0\u25fb\u25fc\u3030\u303d\u3297\u3299"
)
# Thai, Lao and Khmer are written without spaces: a zero-width space between two letters marks a word break.
_WORD_BREAK_SCRIPTS = frozenset({"THAI", "LAO", "KHMER"})
# A `<document>` tag in any case, with white space inside or attributes: the provider's data delimiter.
_DOCUMENT_TAG = re.compile(r"<\s*(/?)\s*document\b[^>]*>", re.IGNORECASE)
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
    decoded = " ".join(
        part for part in (_decode_tags(unflagged), _decode_selectors(unflagged)) if part
    ).strip()

    stripped = _QUIET_CHARS.sub("", _strip_hidden(unflagged))
    cleaned = clean_text(unicodedata.normalize("NFKC", stripped), multiline=True)
    delimiters = len(_DOCUMENT_TAG.findall(cleaned)) or len(_DOCUMENT_TAG.findall(skeleton(cleaned)))
    cleaned = _DOCUMENT_TAG.sub(_neutralise_document_tag, cleaned)

    signals: list[str] = []
    if decoded:
        signals.append(f"hidden text: {decoded[:_EVIDENCE_MAX]}")
    elif suspicious:
        signals.append(f"hidden characters ({len(suspicious)})")
    if delimiters:
        signals.append(f"document delimiter tag in the text ({delimiters})")
    for phrase in find_injection_phrases(skeleton(cleaned)) + (
        find_injection_phrases(skeleton(decoded)) if decoded else []
    ):
        if phrase not in signals:
            signals.append(phrase)

    text, redactions = redact(cleaned)
    return PreparedText(text=text, injection=signals, hidden_count=len(suspicious), redactions=redactions)


def _neutralise_document_tag(match: re.Match[str]) -> str:
    return "[/document]" if match.group(1) else "[document]"


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


def _decode_selectors(text: str) -> str:
    """A run of variation selectors is a known way to carry bytes after a visible character: U+FE00 to
    U+FE0F are the values 0 to 15 and U+E0100 to U+E01EF the values 16 to 255. A lone selector is not a
    message, so only runs of two or more are decoded."""
    decoded = ""
    for run in _SELECTOR_RUN.findall(text):
        data = bytes(ord(c) - 0xFE00 if ord(c) <= 0xFE0F else ord(c) - 0xE0100 + 16 for c in run)
        decoded += "".join(c for c in data.decode("utf-8", errors="ignore") if c.isprintable())
    return decoded


def _without_ordinary_flags(text: str) -> str:
    """Drop the tag run of the England, Scotland and Wales flags (keeping the flag itself). Every other tag
    run, a longer one after a black flag included, stays in the text and is flagged as hidden."""
    return _FLAG_SEQUENCE.sub(_BLACK_FLAG, text)


def _strip_hidden(text: str) -> str:
    return _ALL_HIDDEN.sub(lambda m: m.group() if _is_emoji_selector(m.string, m.start()) else "", text)


def _suspicious_hidden(text: str) -> list[str]:
    found: list[str] = []
    for match in _ALL_HIDDEN.finditer(text):
        char, index = match.group(), match.start()
        if char == "\ufeff" and index == 0:
            continue
        if _is_emoji_selector(text, index):
            continue
        if char in "\u200b\u200c\u200d" and _is_joiner_in_writing(text, index):
            continue
        found.append(char)
    return found


def _is_emoji_selector(text: str, index: int) -> bool:
    """U+FE0F directly after an emoji is how an emoji is asked for in colour: ordinary writing."""
    if text[index] != "\ufe0f" or index == 0:
        return False
    before = text[index - 1]
    if before in "#*0123456789":
        return text[index + 1 : index + 2] == "\u20e3"
    return before in _SELECTOR_BASES or (before != "\ufe0f" and _is_emoji(before))


def _is_joiner_in_writing(text: str, index: int) -> bool:
    if index == 0 or index + 1 >= len(text):
        return False
    before, after = text[index - 1], text[index + 1]
    if text[index] == "\u200b":
        return _script(before) in _WORD_BREAK_SCRIPTS and _script(after) in _WORD_BREAK_SCRIPTS
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
# Two 4-digit groups split by a space are only a phone number with a prefix or a phone word nearby: "area
# 3000 2500 sqft" is not one. The unbroken and the hyphenated forms are always masked.
_PHONE = re.compile(
    r"(?<![A-Za-z0-9])(?P<prefix>(?:\+|00)?65[ -]?)?"
    r"[3689]\d{3}(?P<sep>[ -]?)(?P<tail>\d{4})(?![A-Za-z0-9])"
)
_PHONE_WORD = re.compile(
    r"\b(?:tel|telephone|phones?|mobile|handphone|hp|contacts?|call|calls|calling)\b", re.IGNORECASE
)
_PHONE_WORDS_BEFORE = 4
_PHONE_WORDS_AFTER = 1
_DDMMYYYY = re.compile(r"3[01](?:0[1-9]|1[0-2])(?:19|20)\d{2}")
_KEPT = 4


def redact(text: str, *, phone_context: bool = False) -> tuple[str, int]:
    """Mask NRIC/FIN and Singapore phone numbers, keeping the last 4 characters. Returns the text and how
    many numbers were masked. `phone_context` says the text is known to hold a phone number (a form field
    named phone), so the space-separated form needs no prefix or phone word."""
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
        if match.group("sep") == " " and not match.group("prefix") and not phone_context:
            if not _phone_word_near(match.string, match.start(), match.end()):
                return whole
        count += 1
        return "****" + match.group("tail")

    return _PHONE.sub(mask_phone, _NRIC.sub(mask_nric, text)), count


def _phone_word_near(text: str, start: int, end: int) -> bool:
    """A phone word (tel, phone, mobile, hp, contact, call) within a few words of the number."""
    before = " ".join(text[:start].split()[-_PHONE_WORDS_BEFORE:])
    after = " ".join(text[end:].split()[:_PHONE_WORDS_AFTER])
    return bool(_PHONE_WORD.search(before) or _PHONE_WORD.search(after))


def redact_form_section(section: dict[str, Any]) -> dict[str, Any]:
    """The form values sent beside the document, normalised with NFKC and masked the same way as the text,
    so a masked number or a name in the text and the same one in the form compare equal."""
    return {key: _redact_value(value, _is_phone_key(key)) for key, value in section.items()}


def _is_phone_key(key: str) -> bool:
    return any(_PHONE_WORD.fullmatch(part) for part in re.split(r"[^A-Za-z0-9]+", key))


def _redact_value(value: Any, phone_context: bool) -> Any:
    if isinstance(value, str):
        return redact(unicodedata.normalize("NFKC", value), phone_context=phone_context)[0]
    if isinstance(value, dict):
        return {k: _redact_value(v, _is_phone_key(k)) for k, v in value.items()}
    if isinstance(value, list):
        return [_redact_value(v, phone_context) for v in value]
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
