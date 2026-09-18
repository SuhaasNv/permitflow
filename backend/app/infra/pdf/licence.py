"""Renders the licence certificate as a single A4 PDF page with reportlab (US-051).

Pure function of the data: same input, same bytes (modulo reportlab's timestamps, which are pinned).
Text is real text, so pypdf can read it back in tests and an officer can search it.
"""

from io import BytesIO

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import simpleSplit
from reportlab.pdfgen import canvas

from app.domain.licence import ISSUER, LICENCE_TITLE, LicenceData

INK = HexColor("#1b2430")
MUTED = HexColor("#5b6472")
LINE = HexColor("#d7dbe2")
BRAND = HexColor("#a8192a")
WHITE = HexColor("#ffffff")

UNIT = "Food Establishments Unit"

CONDITIONS = (
    "The licence covers the premises and the business named above only and is not transferable.",
    "The premises must be kept in the condition inspected; material changes must be notified first.",
    "The licence must be displayed at the premises and produced to a licensing officer on request.",
)


def _brand_mark(c: canvas.Canvas, x: float, y: float, size: float) -> None:
    """The PermitFlow mark from the design system: rounded red square, three lines and a tick.
    Same geometry as the SVG (32-unit grid), drawn as paths so no image file is needed."""
    u = size / 32
    c.saveState()
    c.setFillColor(BRAND)
    c.roundRect(x, y, size, size, 7 * u, fill=1, stroke=0)
    c.setStrokeColor(WHITE)
    c.setLineWidth(2.6 * u)
    c.setLineCap(1)
    c.setLineJoin(1)
    # SVG y grows downwards; the canvas grows upwards, so rows are mirrored.
    top = y + size
    c.line(x + 9 * u, top - 10 * u, x + 23 * u, top - 10 * u)
    c.line(x + 9 * u, top - 16 * u, x + 18 * u, top - 16 * u)
    c.line(x + 9 * u, top - 22 * u, x + 13 * u, top - 22 * u)
    p = c.beginPath()
    p.moveTo(x + 16.5 * u, top - 22 * u)
    p.lineTo(x + 19 * u, top - 24.5 * u)
    p.lineTo(x + 24 * u, top - 18 * u)
    c.drawPath(p, stroke=1, fill=0)
    c.restoreState()


def _fit_lines(text: str, font: str, size: float, max_width: float, floor: float) -> tuple[float, list[str]]:
    """Largest size at or above the floor at which the text fits in two lines; the lines themselves."""
    while True:
        lines = simpleSplit(text, font, size, max_width)
        if len(lines) <= 2 or size <= floor:
            return size, lines
        size -= 0.5


STRIP_TOP = 42 * mm  # signature strip, measured from the page margin
GAP_ABOVE_STRIP = 10 * mm


def render_licence_pdf(data: LicenceData) -> bytes:
    """Two passes: measure where the body ends with the base spacing, then draw for real with the
    slack shared across the four vertical gaps so a short certificate does not leave a hole above
    the signature strip and a long one still clears it."""
    dry = canvas.Canvas(BytesIO(), pagesize=A4)
    y_end = _draw_page(dry, data, extra=0)
    slack = y_end - (16 * mm + STRIP_TOP + GAP_ABOVE_STRIP)
    extra = max(0.0, min(slack / 4, 6 * mm))

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4, pageCompression=0)
    c.setTitle(f"{LICENCE_TITLE} {data.licence_no}")
    c.setAuthor(ISSUER)
    c.setSubject("Fictional licence certificate produced by PermitFlow for a software demonstration")
    _draw_page(c, data, extra=extra)
    c.showPage()
    c.save()
    return buffer.getvalue()


def _draw_page(c: canvas.Canvas, data: LicenceData, *, extra: float) -> float:
    """Draws the page; returns the y where the body text ends (above the signature strip)."""
    width, height = float(A4[0]), float(A4[1])

    # Frame: one firm rule and one hairline inside it.
    margin = 16 * mm
    c.setStrokeColor(INK)
    c.setLineWidth(1.2)
    c.rect(margin, margin, width - 2 * margin, height - 2 * margin)
    c.setStrokeColor(LINE)
    c.setLineWidth(0.5)
    c.rect(margin + 3 * mm, margin + 3 * mm, width - 2 * margin - 6 * mm, height - 2 * margin - 6 * mm)

    left = margin + 16 * mm
    right = width - margin - 16 * mm
    content_w = right - left

    # Header: mark and wordmark on the left, the two reference numbers on the right.
    y = height - margin - 22 * mm
    _brand_mark(c, left, y - 1 * mm, 10 * mm)
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 17)
    c.drawString(left + 13.5 * mm, y + 4.2 * mm, "PermitFlow")
    c.setFont("Helvetica", 9.5)
    c.setFillColor(MUTED)
    c.drawString(left + 13.5 * mm, y - 0.6 * mm, ISSUER)
    c.setFont("Helvetica", 7.5)
    c.drawRightString(right, y + 7 * mm, "LICENCE NO.")
    c.drawRightString(right, y - 1.2 * mm, "APPLICATION")
    c.setFillColor(INK)
    c.setFont("Courier-Bold", 11)
    c.drawRightString(right, y + 2.6 * mm, data.licence_no)
    c.drawRightString(right, y - 5.6 * mm, data.reference_no)

    y -= 13 * mm
    c.setStrokeColor(INK)
    c.setLineWidth(0.8)
    c.line(left, y, right, y)

    # Title block
    y -= 18 * mm + extra
    c.setFillColor(MUTED)
    c.setFont("Helvetica", 9)
    c.drawCentredString(width / 2, y + 12 * mm, UNIT.upper())
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 28)
    c.drawCentredString(width / 2, y, LICENCE_TITLE)
    c.setFont("Helvetica", 10.5)
    c.setFillColor(MUTED)
    y -= 8.5 * mm
    c.drawCentredString(width / 2, y, "This certifies that the business named below is licensed to operate")
    y -= 5.5 * mm
    c.drawCentredString(
        width / 2, y, "a food establishment at the premises stated, subject to the conditions below."
    )

    # Business
    y -= 16 * mm + extra
    name_size, name_lines = _fit_lines(data.business_name, "Helvetica-Bold", 22, content_w - 6 * mm, 15)
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", name_size)
    for line in name_lines:
        c.drawCentredString(width / 2, y, line)
        y -= name_size * 1.2
    y -= 7.5 * mm - name_size * 1.2
    c.setFont("Helvetica", 10.5)
    c.setFillColor(MUTED)
    entity = f"   ·   {data.entity_type}" if data.entity_type else ""
    c.drawCentredString(width / 2, y, f"UEN {data.uen}{entity}")

    # Particulars: ruled two-column grid, values wrap when the column is too narrow.
    y -= 12 * mm + extra
    rows = [
        ("Premises", f"{data.premises_address}, Singapore {data.postal_code}", "Helvetica"),
        ("Licence holder", data.holder_name, "Helvetica"),
        ("Valid from", data.valid_from.strftime("%d %B %Y"), "Helvetica"),
        ("Valid to", data.valid_to.strftime("%d %B %Y"), "Helvetica"),
        ("Approved by", data.approved_by, "Helvetica"),
        ("Verification code", data.verification_code, "Courier-Bold"),
    ]
    label_w = 46 * mm
    value_x = left + label_w
    value_w = content_w - label_w
    value_size = 11.5
    line_h = 5.6 * mm
    pad = 3 * mm
    c.setStrokeColor(INK)
    c.setLineWidth(0.8)
    c.line(left, y, right, y)
    for label, value, font in rows:
        lines = simpleSplit(value, font, value_size, value_w)
        row_h = pad * 2 + line_h * max(1, len(lines))
        baseline = y - pad - 4.1 * mm
        c.setFillColor(MUTED)
        c.setFont("Helvetica", 8.5)
        c.drawString(left, baseline, label.upper())
        c.setFillColor(INK)
        c.setFont(font, value_size)
        for k, line in enumerate(lines):
            c.drawString(value_x, baseline - k * line_h, line)
        y -= row_h
        c.setStrokeColor(LINE)
        c.setLineWidth(0.5)
        c.line(left, y, right, y)

    # Conditions
    y -= 9 * mm + extra
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 10.5)
    c.drawString(left, y, "Conditions")
    c.setFont("Helvetica", 9)
    c.setFillColor(MUTED)
    for n, cond in enumerate(CONDITIONS, start=1):
        for k, line in enumerate(simpleSplit(cond, "Helvetica", 9, content_w - 6 * mm)):
            y -= 5 * mm
            if k == 0:
                c.drawString(left, y, f"{n}.")
            c.drawString(left + 6 * mm, y, line)

    # Signature strip, pinned to the bottom of the frame.
    y_end = float(y)
    y = margin + STRIP_TOP
    c.setStrokeColor(INK)
    c.setLineWidth(0.8)
    c.line(left, y, right, y)
    c.setFillColor(MUTED)
    c.setFont("Helvetica", 8.5)
    c.drawString(left, y - 7 * mm, "ISSUED ON")
    c.setFillColor(INK)
    c.setFont("Helvetica", 10.5)
    c.drawString(left, y - 12 * mm, data.valid_from.strftime("%d %B %Y"))
    c.setFillColor(MUTED)
    c.setFont("Helvetica", 8.5)
    c.drawString(left, y - 19 * mm, "VERIFY WITH")
    c.setFillColor(INK)
    c.setFont("Courier-Bold", 9.5)
    c.drawString(left, y - 24 * mm, f"{data.licence_no}  {data.verification_code}")

    sig_w = 76 * mm
    sig_x = right - sig_w
    sig_y = y - 15 * mm
    c.setStrokeColor(INK)
    c.setLineWidth(0.8)
    c.line(sig_x, sig_y, right, sig_y)
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 10.5)
    c.drawString(sig_x, sig_y - 5 * mm, data.approved_by)
    c.setFillColor(MUTED)
    c.setFont("Helvetica", 8.5)
    c.drawString(sig_x, sig_y - 9.5 * mm, f"Licensing officer, {UNIT}")
    issued = data.valid_from.strftime("%d %B %Y")
    c.drawString(sig_x, sig_y - 14 * mm, f"Signed electronically in PermitFlow, {issued}")

    # Footer
    c.setFont("Helvetica", 7.5)
    c.setFillColor(MUTED)
    c.drawCentredString(
        width / 2,
        margin + 7 * mm,
        "Fictional document produced by PermitFlow for a software demonstration. Not issued by any authority",
    )

    if data.preview:
        c.saveState()
        c.setFillColor(BRAND)
        c.setFillAlpha(0.14)
        c.setFont("Helvetica-Bold", 54)
        c.translate(width / 2, height / 2)
        c.rotate(35)
        c.drawCentredString(0, 0, "PREVIEW, NOT ISSUED")
        c.restoreState()

    return y_end
