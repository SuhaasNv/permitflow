"""Renders the licence certificate as a single A4 PDF page with reportlab (US-051).

Pure function of the data: same input, same bytes (modulo reportlab's timestamps, which are pinned).
Text is real text, so pypdf can read it back in tests and an officer can search it.
"""

from io import BytesIO

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from app.domain.licence import ISSUER, LICENCE_TITLE, LicenceData

INK = HexColor("#1b2430")
MUTED = HexColor("#5b6472")
LINE = HexColor("#d7dbe2")
BRAND = HexColor("#a8192a")
SOFT = HexColor("#f6f7f9")


def render_licence_pdf(data: LicenceData) -> bytes:
    buffer = BytesIO()
    width, height = A4
    c = canvas.Canvas(buffer, pagesize=A4, pageCompression=0)
    c.setTitle(f"{LICENCE_TITLE} {data.licence_no}")
    c.setAuthor(ISSUER)
    c.setSubject("Fictional licence certificate produced by PermitFlow for a software demonstration")

    # Frame
    margin = 18 * mm
    c.setStrokeColor(INK)
    c.setLineWidth(1.2)
    c.rect(margin, margin, width - 2 * margin, height - 2 * margin)
    c.setStrokeColor(LINE)
    c.setLineWidth(0.5)
    c.rect(margin + 3 * mm, margin + 3 * mm, width - 2 * margin - 6 * mm, height - 2 * margin - 6 * mm)

    # Header
    x = margin + 14 * mm
    y = height - margin - 22 * mm
    c.setFillColor(BRAND)
    c.rect(x, y + 2 * mm, 8 * mm, 8 * mm, fill=1, stroke=0)
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(x + 11 * mm, y + 4 * mm, "PermitFlow")
    c.setFont("Helvetica", 10)
    c.setFillColor(MUTED)
    c.drawString(x + 11 * mm, y - 1 * mm, ISSUER)
    c.drawRightString(width - margin - 14 * mm, y + 4 * mm, f"Licence no. {data.licence_no}")
    c.drawRightString(width - margin - 14 * mm, y - 1 * mm, f"Application {data.reference_no}")

    # Title
    y -= 24 * mm
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 26)
    c.drawCentredString(width / 2, y, LICENCE_TITLE)
    c.setFont("Helvetica", 11)
    c.setFillColor(MUTED)
    y -= 8 * mm
    intro = "This certifies that the business named below is licensed to operate a food establishment"
    c.drawCentredString(width / 2, y, intro)
    y -= 5.5 * mm
    c.drawCentredString(width / 2, y, "at the premises stated, subject to the conditions of the licence.")

    # Business
    y -= 18 * mm
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(width / 2, y, data.business_name)
    y -= 7 * mm
    c.setFont("Helvetica", 11)
    c.setFillColor(MUTED)
    entity = f"  ·  {data.entity_type}" if data.entity_type else ""
    c.drawCentredString(width / 2, y, f"UEN {data.uen}{entity}")

    # Fields table
    y -= 16 * mm
    rows = [
        ("Premises", f"{data.premises_address}, Singapore {data.postal_code}"),
        ("Licence holder", data.holder_name),
        ("Valid from", data.valid_from.strftime("%d %B %Y")),
        ("Valid to", data.valid_to.strftime("%d %B %Y")),
        ("Approved by", data.approved_by),
        ("Verification code", data.verification_code),
    ]
    table_x = margin + 22 * mm
    table_w = width - 2 * margin - 44 * mm
    row_h = 11 * mm
    c.setFillColor(SOFT)
    c.rect(table_x, y - row_h * len(rows) + 3 * mm, table_w, row_h * len(rows), fill=1, stroke=0)
    for i, (label, value) in enumerate(rows):
        yy = y - i * row_h
        c.setFillColor(MUTED)
        c.setFont("Helvetica", 9.5)
        c.drawString(table_x + 5 * mm, yy - 3 * mm, label.upper())
        c.setFillColor(INK)
        c.setFont("Helvetica-Bold" if label == "Verification code" else "Helvetica", 12)
        c.drawString(table_x + 52 * mm, yy - 3 * mm, value)
        if i < len(rows) - 1:
            c.setStrokeColor(LINE)
            c.line(table_x + 5 * mm, yy - row_h + 3.5 * mm, table_x + table_w - 5 * mm, yy - row_h + 3.5 * mm)

    # Conditions
    y = y - row_h * len(rows) - 12 * mm
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 10.5)
    c.drawString(table_x, y, "Conditions")
    c.setFont("Helvetica", 9.5)
    c.setFillColor(MUTED)
    conditions = [
        "The licence covers the premises and the business named above only and is not transferable.",
        "The premises must be kept in the condition inspected; material changes must be notified first.",
        "The licence must be displayed at the premises and produced to a licensing officer on request.",
    ]
    for line in conditions:
        y -= 5.5 * mm
        c.drawString(table_x, y, f"·  {line}")

    # Signature block
    y = margin + 34 * mm
    c.setStrokeColor(INK)
    c.setLineWidth(0.8)
    c.line(table_x, y, table_x + 70 * mm, y)
    c.setFillColor(INK)
    c.setFont("Helvetica", 10)
    c.drawString(table_x, y - 5 * mm, data.approved_by)
    c.setFillColor(MUTED)
    c.setFont("Helvetica", 9)
    c.drawString(table_x, y - 9.5 * mm, "Licensing officer, " + ISSUER)
    c.drawString(table_x, y - 14 * mm, f"Issued {data.valid_from.strftime('%d %B %Y')}")

    # Footer
    c.setFont("Helvetica", 7.5)
    c.setFillColor(MUTED)
    c.drawCentredString(
        width / 2,
        margin + 8 * mm,
        "Fictional document produced by PermitFlow for a software demonstration. Not issued by any authority",
    )

    if data.preview:
        c.saveState()
        c.setFillColor(HexColor("#a8192a"))
        c.setFillAlpha(0.14)
        c.setFont("Helvetica-Bold", 54)
        c.translate(width / 2, height / 2)
        c.rotate(35)
        c.drawCentredString(0, 0, "PREVIEW, NOT ISSUED")
        c.restoreState()

    c.showPage()
    c.save()
    return buffer.getvalue()
