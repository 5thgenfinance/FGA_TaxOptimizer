"""Golden regression: the saved TaxRetirementOptimizer.xlsx scenario (MFJ, 2026)."""
from datetime import date
from decimal import Decimal

import pytest

from app.calc.engine import compute
from app.models import FilerInputs


@pytest.fixture()
def golden_inputs():
    return FilerInputs(
        tax_year=2026, filing_status="Jointly", dob=date(1952, 4, 14), spouse_dob=date(1974, 9, 30),
        prior_ye_ira_balance=1_000_000, qualified_dividends=1_800, taxable_interest=900,
        ordinary_dividends=2_400, short_term_gain_loss=-3_000, wages_and_tips=145_000,
        long_term_capital_gains=6_000, schedule_a_deductions=12_000, tax_withheld=16_500,
    )


def approx(value, expected, places=2):
    assert round(value, places) == Decimal(str(expected)).quantize(Decimal(1).scaleb(-places))


def test_legacy_matches_workbook(golden_inputs, tables):
    r = compute(golden_inputs, tables, legacy=True, as_of_year=2026)
    approx(r.rmd, 39215.69)
    approx(r.agi, 190515.69)
    assert r.standard_deduction == 37419
    approx(r.adjusted_taxable_income, 153096.69)
    approx(r.taxable_ordinary, 145296.69)
    approx(r.taxable_preferential, 7800)
    approx(r.ordinary_tax, 21389.27)
    approx(r.ltcg_tax, 1170)
    approx(r.regular_tax, 22559.27)
    approx(r.net_investment_income, 6300)
    assert r.niit == 0
    approx(r.amt_tentative, 12999.14)
    assert r.amt_owed == 0
    approx(r.total_tax, 22559.27)
    approx(r.due_or_refund, 6059.27)
    approx(r.effective_rate, 0.1184, places=4)
    approx(r.ltcg_effective_rate, 0.15, places=2)
    assert r.taxable_ss_share is None
    assert [a.amount for a in r.ltcg_allocations] == [0, Decimal(7800), 0]
    assert len(r.ordinary_allocations) == 6


def test_fixed_mode_same_tax_and_stacked_amt(golden_inputs, tables):
    r = compute(golden_inputs, tables, legacy=False)
    approx(r.total_tax, 22559.27)
    approx(r.due_or_refund, 6059.27)
    assert r.salt_addback == 0
    approx(r.amt_tentative, 1325.14)  # gains fall in the 0% bracket, not a flat 15%
    assert any("SALT" in w for w in r.warnings)


def test_alias_status_and_zero_agi(tables):
    r = compute(FilerInputs(tax_year=2026, filing_status="MFJ", dob=date(1990, 1, 1)), tables)
    assert r.filing_status == "Jointly"
    assert r.agi == 0 and r.effective_rate is None and r.total_tax == 0


def test_top_bracket_is_taxed_at_37_percent(tables):
    inputs = FilerInputs(tax_year=2026, filing_status="Single", dob=date(1980, 1, 1), wages_and_tips=900_000)
    fixed = compute(inputs, tables)
    assert not any("highest bracket" in w for w in fixed.warnings)
    assert [a.bracket.rate for a in fixed.ordinary_allocations][-1] == Decimal("0.37")
    assert fixed.ordinary_allocations[-1].amount == fixed.taxable_ordinary - Decimal(640_600)
    legacy = compute(inputs, tables, legacy=True, as_of_year=2026)
    assert any("highest bracket" in w for w in legacy.warnings)  # six-row workbook estimator


def test_unsupported_year_raises(tables):
    from app.calc.common import MissingDataError
    with pytest.raises(MissingDataError):
        compute(FilerInputs(tax_year=2024, filing_status="Single", dob=date(1980, 1, 1)), tables)


def test_deduction_exceeding_income_clamps_in_fixed_mode(tables):
    inputs = FilerInputs(tax_year=2026, filing_status="Single", dob=date(1980, 1, 1),
                         long_term_capital_gains=1_000, schedule_a_deductions=0)
    fixed = compute(inputs, tables, legacy=False)
    legacy = compute(inputs, tables, legacy=True, as_of_year=2026)
    assert fixed.adjusted_taxable_income == 0 and fixed.taxable_preferential == 0
    assert legacy.adjusted_taxable_income < 0
