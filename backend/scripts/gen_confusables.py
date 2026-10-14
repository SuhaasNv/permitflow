"""Regenerate `app/domain/confusables_data.py` from the Unicode TR39 `confusables.txt` (US-102).

    curl -O https://www.unicode.org/Public/security/latest/confusables.txt
    uv run python scripts/gen_confusables.py confusables.txt

Only the part the injection detector needs is kept: a single non-ASCII letter or digit that the table maps
to ASCII letters or digits, and that NFKC does not already fold. Punctuation and symbols are dropped (a
Devanagari danda is not a lowercase L to a reader), which keeps the table to about a thousand entries.
The table maps Latin I, l and 1 to one prototype; a capital look-alike of I becomes `I` and a digit becomes
`1` here so the English phrase patterns (case-insensitive) still match.
"""

import sys
import unicodedata
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "app" / "domain" / "confusables_data.py"
LINE_WIDTH = 90


def parse(path: Path) -> tuple[str, dict[str, str]]:
    version = "unknown"
    table: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        if raw.startswith("# Version:"):
            version = raw.split(":", 1)[1].strip()
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        src, tgt = (part.strip() for part in line.split(";")[:2])
        table["".join(chr(int(x, 16)) for x in src.split())] = "".join(chr(int(x, 16)) for x in tgt.split())
    return version, table


def keep(src: str, tgt: str) -> str | None:
    if len(src) != 1 or ord(src) < 128 or not tgt.isascii() or not tgt.isalnum():
        return None
    if unicodedata.category(src)[0] not in "LN":
        return None
    if unicodedata.normalize("NFKC", src).isascii():
        return None
    if tgt == "l":
        if unicodedata.category(src) == "Nd":
            return "1"
        return "I" if src.isupper() else "l"
    return tgt


def escape(char: str) -> str:
    return f"\\u{ord(char):04x}" if ord(char) <= 0xFFFF else f"\\U{ord(char):08x}"


def main(path: Path) -> None:
    version, table = parse(path)
    grouped: dict[str, list[str]] = {}
    for src, tgt in sorted(table.items(), key=lambda kv: ord(kv[0][0])):
        out = keep(src, tgt)
        if out is not None:
            grouped.setdefault(out, []).append(src)
    lines = [
        '"""Look-alike letters that fold to ASCII, generated from Unicode TR39 confusables.txt (US-102).',
        "",
        f"Source: https://www.unicode.org/Public/security/latest/confusables.txt, version {version}.",
        "Unicode data files are used under the Unicode License (https://www.unicode.org/license.txt).",
        "Do not edit by hand: regenerate with `scripts/gen_confusables.py` (see its docstring).",
        '"""',
        "",
        "# ASCII character -> the non-ASCII characters that look like it.",
        "_GROUPS: dict[str, str] = {",
    ]
    for ascii_char in sorted(grouped):
        parts: list[str] = []
        current = ""
        for src in grouped[ascii_char]:
            token = escape(src)
            if len(current) + len(token) > LINE_WIDTH:
                parts.append(current)
                current = ""
            current += token
        parts.append(current)
        lines.append(f"    {ascii_char!r}: (")
        lines.extend(f'        "{p}"' for p in parts)
        lines.append("    ),")
    lines += [
        "}",
        "",
        "CONFUSABLES: dict[int, str] = {",
        "    ord(src): ascii_char for ascii_char, group in _GROUPS.items() for src in group",
        "}",
        "",
    ]
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {OUT} ({sum(len(v) for v in grouped.values())} entries, Unicode {version})")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
