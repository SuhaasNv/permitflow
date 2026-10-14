"""Render an attack into a real PDF or PNG (US-106). Stdlib and Pillow only; deterministic, so a promoted
fixture is byte-for-byte reproducible.

A `Span` is one line of the page. Beyond size and colour it can be invisible (text render mode 3), and it can
carry a `cmap`: what the extractor reads for a character can differ from the glyph a reader sees. That is how
a PDF hides zero-width characters, Tag-block characters and look-alike letters: the file draws plain Latin
glyphs and its /ToUnicode table says something else. The PDF is written by hand because the usual libraries
only emit the text they are given, never a contradicting extraction map.
"""

from __future__ import annotations

import io
from dataclasses import dataclass, field

from PIL import Image, ImageDraw, ImageFont


@dataclass(frozen=True)
class Span:
    text: str  # what the glyphs show
    size: float = 11.0
    gray: float = 0.0  # fill: 0 black, 1 white
    invisible: bool = False  # text render mode 3: not painted, still extracted
    cmap: dict[str, str] = field(default_factory=dict)  # shown character -> what the extractor reads


def _esc(text: str) -> bytes:
    return (
        text.encode("latin-1", "replace").replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)")
    )


def _utf16(text: str) -> str:
    return text.encode("utf-16-be").hex().upper()


def _to_unicode(span: Span) -> bytes:
    pairs = {c: span.cmap.get(c, c) for c in dict.fromkeys(span.text)}
    entries = "\n".join(f"<{ord(c):02X}> <{_utf16(v)}>" for c, v in pairs.items())
    return (
        "/CIDInit /ProcSet findresource begin 12 dict begin begincmap\n"
        "/CMapName /Adobe-Identity-UCS def /CMapType 2 def\n"
        "1 begincodespacerange <00> <FF> endcodespacerange\n"
        f"{len(pairs)} beginbfchar\n{entries}\nendbfchar\nendcmap\n"
        "CMapName currentdict /CMap defineresource pop end end"
    ).encode("ascii")


def render_pdf(spans: list[Span], info: dict[str, str] | None = None) -> bytes:
    """One A4 page, one span per line from the top. `info` becomes the PDF metadata (/Info)."""
    objects: list[bytes] = []  # object n is objects[n - 1]

    def add(body: bytes) -> int:
        objects.append(body)
        return len(objects)

    def stream(data: bytes) -> bytes:
        return b"<< /Length %d >>\nstream\n" % len(data) + data + b"\nendstream"

    catalog, pages, page, content = add(b""), add(b""), add(b""), add(b"")
    base_font = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")
    fonts = {"F0": base_font}
    ops: list[bytes] = []
    y = 800.0
    for i, span in enumerate(spans):
        name = "F0"
        if span.cmap:
            name = f"F{i + 1}"
            to_unicode = add(stream(_to_unicode(span)))
            fonts[name] = add(
                b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding "
                b"/ToUnicode %d 0 R >>" % to_unicode
            )
        y -= max(span.size, 4.0) + 5
        ops.append(
            b"BT /%s %g Tf %g g %d Tr 50 %g Td (%s) Tj ET"
            % (name.encode(), span.size, span.gray, 3 if span.invisible else 0, y, _esc(span.text))
        )
    objects[content - 1] = stream(b"\n".join(ops))
    resources = b" ".join(b"/%s %d 0 R" % (k.encode(), v) for k, v in fonts.items())
    objects[page - 1] = (
        b"<< /Type /Page /Parent %d 0 R /MediaBox [0 0 595 842] /Contents %d 0 R "
        b"/Resources << /Font << %s >> >> >>" % (pages, content, resources)
    )
    objects[pages - 1] = b"<< /Type /Pages /Kids [%d 0 R] /Count 1 >>" % page
    root = b"/Root %d 0 R" % catalog
    objects[catalog - 1] = b"<< /Type /Catalog /Pages %d 0 R >>" % pages
    trailer_info = b""
    if info:
        fields = b" ".join(b"/%s (%s)" % (k.encode(), _esc(v)) for k, v in info.items())
        trailer_info = b" /Info %d 0 R" % add(b"<< %s >>" % fields)

    out = io.BytesIO()
    out.write(b"%PDF-1.4\n")
    offsets = []
    for n, body in enumerate(objects, 1):
        offsets.append(out.tell())
        out.write(b"%d 0 obj\n%s\nendobj\n" % (n, body))
    xref = out.tell()
    out.write(b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1))
    for offset in offsets:
        out.write(b"%010d 00000 n \n" % offset)
    out.write(
        b"trailer\n<< /Size %d %s%s >>\nstartxref\n%d\n%%%%EOF\n"
        % (len(objects) + 1, root, trailer_info, xref)
    )
    return out.getvalue()


def render_png(spans: list[Span]) -> bytes:
    """The same page as an image: what a reader (or an OCR step) would see. Invisible spans are not painted;
    white text is painted one level off white, the way a near-invisible scan watermark would be."""
    image = Image.new("RGB", (800, 1000), "white")
    draw = ImageDraw.Draw(image)
    y = 40
    for span in spans:
        if not span.invisible:
            level = min(int(span.gray * 255), 254)
            font = ImageFont.load_default(size=max(int(span.size * 1.6), 4))
            draw.text((40, y), span.text, fill=(level, level, level), font=font)
        y += int(max(span.size, 4.0) * 1.6) + 8
    out = io.BytesIO()
    image.save(out, "PNG")
    return out.getvalue()
