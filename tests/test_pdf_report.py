import io
from datetime import date, datetime

import pytest

from app import pdf_report
from app.calc.engine import compute
from app.models import FilerInputs

NOW = datetime(2026, 11, 16, 20, 0)


def golden(tables, legacy=True):
    inputs = FilerInputs(
        tax_year=2026, filing_status="Jointly", dob=date(1952, 4, 14), spouse_dob=date(1974, 9, 30),
        prior_ye_ira_balance=1_000_000, qualified_dividends=1_800, taxable_interest=900,
        ordinary_dividends=2_400, short_term_gain_loss=-3_000, wages_and_tips=145_000,
        long_term_capital_gains=6_000, schedule_a_deductions=12_000, tax_withheld=16_500,
    )
    return inputs, compute(inputs, tables, legacy=legacy, as_of_year=2026)


def make_pdf(tables, title="Maxwell 2026 Roth Study", legacy=True, mutate=None):
    inputs, result = golden(tables, legacy)
    if mutate:
        mutate(result)
    return pdf_report.build_pdf(result, inputs, tables, title, "2026-11-16T18:53:00", now=NOW)


def pdf_text(data: bytes) -> str:
    pypdf = pytest.importorskip("pypdf")
    reader = pypdf.PdfReader(io.BytesIO(data))
    return " ".join(" ".join(page.extract_text().split()) for page in reader.pages)


def test_output_is_a_pdf(tables):
    data = make_pdf(tables)
    assert data.startswith(b"%PDF") and data.rstrip().endswith(b"%%EOF")
    assert len(data) > 3_000


def test_contains_title_figures_and_inputs(tables):
    text = pdf_text(make_pdf(tables))
    for expected in ["Maxwell 2026 Roth Study", "Tax year 2026 | Jointly", "Workbook (legacy) mode",
                     "Scenario last updated 2026-11-16T18:53:00", "Report generated 2026-11-16 20:00",
                     "Total tax $22,559", "Amount due", "$6,059", "11.84%", "Adjusted gross income $190,516",
                     "Ordinary income brackets", "Long-term capital gains brackets",
                     "Date of birth 1952-04-14", "Wages and tips $145,000",
                     "Schedule A state, local and property taxes Not entered",
                     "planning purposes only"]:
        assert expected in text, expected


def test_default_mode_has_no_legacy_label_but_shows_all_brackets(tables):
    text = pdf_text(make_pdf(tables, legacy=False))
    assert "legacy" not in text
    assert "No limit" in text
    assert "SALT is blank" in text


def test_refund_and_warnings(tables):
    def change(result):
        result.due_or_refund = -result.tax_paid
        result.warnings = ["Check this input"]
    text = pdf_text(make_pdf(tables, mutate=change))
    assert "Refund" in text and "Note: Check this input" in text


def test_title_with_markup_characters(tables):
    text = pdf_text(make_pdf(tables, title="Smith & Jones <draft>"))
    assert "Smith & Jones <draft>" in text


def test_blank_title_falls_back_to_default(tables):
    assert "Tax Retirement Optimizer Scenario" in pdf_text(make_pdf(tables, title="  "))


def test_long_scenario_spans_pages_without_error(tables):
    # all optional inputs entered and a warning list that forces extra content
    def change(result):
        result.warnings = [f"Warning number {i} " + "x" * 80 for i in range(40)]
    data = make_pdf(tables, mutate=change)
    pypdf = pytest.importorskip("pypdf")
    assert len(pypdf.PdfReader(io.BytesIO(data)).pages) >= 2


def test_filename():
    assert pdf_report.pdf_filename("Maxwell 2026: Roth/Conversion!") == "Maxwell_2026_Roth_Conversion.pdf"
    assert pdf_report.pdf_filename("???") == "scenario.pdf"
