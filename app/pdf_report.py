"""PDF report for a scenario, built with reportlab (no Streamlit import)."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Image, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app import report, scenario_io

if TYPE_CHECKING:
    from app.calc.engine import TaxResult
    from app.models import FilerInputs
    from app.tables import Tables

DISCLAIMER = (
    "This estimate is for planning purposes only. It uses the tax tables loaded in the "
    "application and simplified calculations, and is not tax, legal or investment advice."
)
NAVY = colors.HexColor("#1F3A5F")
BRONZE = colors.HexColor("#C49A4A")
LIGHT = colors.HexColor("#EEF2F7")
SERIF = "Times-Bold"


def pdf_filename(title: str) -> str:
    return Path(scenario_io.safe_filename(title)).stem + ".pdf"


def logo_flowable(path, width: float):
    """A proportionally scaled logo image, or None if the file is missing or unreadable."""
    if not path or not Path(path).is_file():
        return None
    try:
        pixel_width, pixel_height = ImageReader(str(path)).getSize()
    except Exception:  # an unreadable image must not break the report
        return None
    image = Image(str(path), width=width, height=width * pixel_height / pixel_width)
    image.hAlign = "LEFT"
    return image


def input_value(row, value) -> str:
    """Display text for one input value."""
    if value is None:
        return "Not entered"
    if row.Type == "money":
        return report.fmt_money(Decimal(value))
    if row.Type == "date":
        return value.isoformat()
    return str(value)


def input_groups(inputs: FilerInputs, tables: Tables) -> list[tuple[str, list[tuple[str, str]]]]:
    """Inputs grouped as in the form: (group, [(label, display value)])."""
    groups: dict[str, list[tuple[str, str]]] = {}
    for row in tables.rows("tblInputMap"):
        value = getattr(inputs, row.Field)
        groups.setdefault(row.Group, []).append((row.Label, input_value(row, value)))
    return list(groups.items())


def _styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("title", parent=base["Title"], fontName=SERIF, textColor=NAVY,
                                fontSize=20, leading=24, alignment=0),
        "sub": ParagraphStyle("sub", parent=base["Normal"], textColor=colors.HexColor("#555555"), fontSize=9, leading=12),
        "h2": ParagraphStyle("h2", parent=base["Heading2"], fontName=SERIF, textColor=NAVY, fontSize=12,
                             spaceBefore=10, spaceAfter=4),
        "body": ParagraphStyle("body", parent=base["Normal"], fontSize=9, leading=12),
        "warn": ParagraphStyle("warn", parent=base["Normal"], fontSize=9, leading=12, textColor=colors.HexColor("#8A4B00"),
                               backColor=colors.HexColor("#FFF4E0"), borderPadding=4, spaceAfter=4),
        "small": ParagraphStyle("small", parent=base["Normal"], fontSize=7.5, leading=10, textColor=colors.HexColor("#666666")),
    }


def _table(rows, widths, header: bool = False, right_from: int = 1) -> Table:
    table = Table(rows, colWidths=widths, repeatRows=1 if header else 0)
    style = [
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ROWBACKGROUNDS", (0, 1 if header else 0), (-1, -1), [colors.white, LIGHT]),
        ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.HexColor("#CCCCCC")),
        ("ALIGN", (right_from, 0), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]
    if header:
        style += [("BACKGROUND", (0, 0), (-1, 0), NAVY), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                  ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold")]
    table.setStyle(TableStyle(style))
    return table


def _bracket_table(allocations) -> Table:
    records = report.allocation_records(allocations)
    columns = ["Bucket", "Rate", "Up to", "Income in bracket", "Tax"]
    rows = [columns] + [[str(r[c]) for c in columns] for r in records]
    return _table(rows, [0.7 * inch, 0.8 * inch, 1.3 * inch, 1.8 * inch, 1.4 * inch], header=True, right_from=1)


def build_pdf(result: TaxResult, inputs: FilerInputs, tables: Tables, title: str,
              last_updated: str, now: datetime | None = None, logo=None) -> bytes:
    """Render the scenario inputs and results as a PDF and return its bytes.

    ``logo`` is an optional image file (for example a brand ribbon on a white background).
    """
    title = (title or "").strip() or scenario_io.DEFAULT_TITLE
    generated = (now or datetime.now()).strftime("%Y-%m-%d %H:%M")
    st = _styles()
    width = 7.0 * inch
    label_w = 4.9 * inch

    story = []
    brand_logo = logo_flowable(logo, 2.2 * inch)
    if brand_logo is not None:
        story += [brand_logo, Spacer(1, 8)]
    story += [
        Paragraph(escape(title), st["title"]),
        Paragraph(escape(f"Tax year {result.tax_year} | {result.filing_status}"
                         + (" | Workbook (legacy) mode" if result.legacy else "")), st["sub"]),
        Paragraph(escape(f"Scenario last updated {last_updated} | Report generated {generated}"), st["sub"]),
        Spacer(1, 10),
    ]

    headline = [
        ["Total tax", report.due_label(result), "Effective rate (of AGI)"],
        [report.fmt_money(result.total_tax), report.fmt_money(abs(result.due_or_refund)),
         report.fmt_rate(result.effective_rate)],
    ]
    head = Table(headline, colWidths=[width / 3] * 3)
    head.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, 0), 8), ("FONTSIZE", (0, 1), (-1, 1), 16),
        ("FONTNAME", (0, 1), (-1, 1), SERIF), ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("BACKGROUND", (0, 1), (-1, 1), LIGHT), ("TOPPADDING", (0, 1), (-1, 1), 8), ("BOTTOMPADDING", (0, 1), (-1, 1), 8),
        ("LINEBELOW", (0, 1), (-1, 1), 1.5, BRONZE),
    ]))
    story += [head, Spacer(1, 6)]

    for warning in result.warnings:
        story.append(Paragraph(escape(f"Note: {warning}"), st["warn"]))

    for section_title, rows in report.sections(result):
        story.append(KeepTogether([Paragraph(escape(section_title), st["h2"]),
                                   _table([[a, b] for a, b in rows], [label_w, width - label_w])]))

    story.append(KeepTogether([Paragraph("Ordinary income brackets", st["h2"]),
                               _bracket_table(result.ordinary_allocations)]))
    story.append(KeepTogether([Paragraph("Long-term capital gains brackets", st["h2"]),
                               _bracket_table(result.ltcg_allocations)]))

    story.append(Paragraph("Scenario inputs", st["h2"]))
    for group, rows in input_groups(inputs, tables):
        story.append(KeepTogether([Paragraph(f"<b>{escape(group)}</b>", st["body"]),
                                   _table([[a, b] for a, b in rows], [label_w, width - label_w])]))
        story.append(Spacer(1, 4))

    story += [Spacer(1, 8), Paragraph(escape(DISCLAIMER), st["small"])]

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(BRONZE)
        canvas.setLineWidth(0.75)
        canvas.line(0.75 * inch, 0.65 * inch, letter[0] - 0.75 * inch, 0.65 * inch)
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(colors.HexColor("#666666"))
        canvas.drawString(0.75 * inch, 0.5 * inch, title[:90])
        canvas.drawRightString(letter[0] - 0.75 * inch, 0.5 * inch, f"Page {doc.page}")
        canvas.restoreState()

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, leftMargin=0.75 * inch, rightMargin=0.75 * inch,
                            topMargin=0.75 * inch, bottomMargin=0.8 * inch, title=title,
                            author="FGA Tax Optimizer")
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return buffer.getvalue()
