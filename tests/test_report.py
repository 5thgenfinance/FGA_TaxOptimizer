from datetime import date
from decimal import Decimal

from app import report
from app.calc.engine import compute
from app.models import FilerInputs


def golden_result(tables, legacy=True):
    inputs = FilerInputs(
        tax_year=2026, filing_status="Jointly", dob=date(1952, 4, 14), spouse_dob=date(1974, 9, 30),
        prior_ye_ira_balance=1_000_000, qualified_dividends=1_800, taxable_interest=900,
        ordinary_dividends=2_400, short_term_gain_loss=-3_000, wages_and_tips=145_000,
        long_term_capital_gains=6_000, schedule_a_deductions=12_000, tax_withheld=16_500,
    )
    return compute(inputs, tables, legacy=legacy, as_of_year=2026)


def test_money_and_rate_formats():
    assert report.fmt_money(Decimal("22559.27")) == "$22,559"
    assert report.fmt_money(Decimal("-1234.5")) == "-$1,234"
    assert report.fmt_money(Decimal(0)) == "$0"
    assert report.fmt_rate(Decimal("0.1184116")) == "11.84%"
    assert report.fmt_rate(None) == "n/a"


def test_sections_match_golden(tables):
    result = golden_result(tables)
    flat = {label: value for _, rows in report.sections(result) for label, value in rows}
    assert flat["Total tax"] == "$22,559"
    assert flat["Amount due"] == "$6,059"
    assert flat["Adjusted gross income"] == "$190,516"
    assert flat["Standard deduction"] == "$37,419"
    assert flat["Effective rate (of AGI)"] == "11.84%"
    assert [t for t, _ in report.sections(result)] == [
        "Income", "Deductions", "Tax", "Alternative minimum tax", "Summary"]


def test_refund_label(tables):
    result = golden_result(tables)
    result.due_or_refund = Decimal(-500)
    assert report.due_label(result) == "Refund"


def test_allocation_records(tables):
    records = report.allocation_records(golden_result(tables).ordinary_allocations)
    assert len(records) == 6
    assert records[0] == {"Bucket": 1, "Rate": "10%", "Up to": "$24,800",
                          "Income in bracket": "$24,800", "Tax": "$2,480"}
    ltcg = report.allocation_records(golden_result(tables).ltcg_allocations)
    assert ltcg[1]["Income in bracket"] == "$7,800" and ltcg[1]["Tax"] == "$1,170"
