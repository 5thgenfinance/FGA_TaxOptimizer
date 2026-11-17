"""Phase 3: 2026/2027 data checks against IRS figures, and the planned fixes."""
from datetime import date
from decimal import Decimal

import pytest

from app.calc import amt, deductions, ltcg, niit, ordinary
from app.calc.engine import compute
from app.models import FilerInputs

D = Decimal


@pytest.mark.parametrize("income,tax", [
    (25_600, "2560.00"), (104_050, "11974.00"), (218_250, "37098.00"),
    (416_650, "84714.00"), (529_100, "120698.00"), (793_650, "213290.50"),
])
def test_2027_joint_tax_matches_rev_proc_2026_35(tables, income, tax):
    assert ordinary.income_tax(income, tables, 2027, "Jointly") == D(tax)


@pytest.mark.parametrize("income,tax", [
    (12_800, "1280.00"), (52_025, "5987.00"), (109_125, "18549.00"),
    (208_325, "42357.00"), (264_550, "60349.00"), (661_375, "199237.75"),
])
def test_2027_single_tax_matches_rev_proc_2026_35(tables, income, tax):
    assert ordinary.income_tax(income, tables, 2027, "Single") == D(tax)


def test_2026_joint_tax_matches_rev_proc_2025_32(tables):
    assert ordinary.income_tax(24_800, tables, 2026, "Jointly") == D(2_480)
    assert ordinary.income_tax(100_800, tables, 2026, "Jointly") == D(11_600)


def test_2026_income_above_old_top_bracket_is_taxed_at_37_percent(tables):
    top = ordinary.income_tax(768_700, tables, 2026, "Jointly")
    assert ordinary.income_tax(868_700, tables, 2026, "Jointly") - top == D(37_000)


def test_2027_ltcg_thresholds(tables):
    single = ltcg.ltcg_brackets(tables, 2027, "Single")
    joint = ltcg.ltcg_brackets(tables, 2027, "Jointly")
    assert [b.limit for b in single[:2]] == [D(51_050), D(563_200)]
    assert [b.limit for b in joint[:2]] == [D(102_100), D(633_600)]
    assert [b.rate for b in single] == [D(0), D("0.15"), D("0.20")]


def test_2027_standard_deduction_with_two_seniors(tables):
    # base 33,200 + 2 x 1,700 age add-on + senior bonus 12,000 (AGI below the 150,000 phase-out)
    result = deductions.standard_deduction_full(date(1950, 5, 1), "Jointly", 33_200, 100_000, 2027,
                                                tables, 2027, date(1950, 5, 1))
    assert result == D(33_200 + 3_400 + 12_000)


def test_2027_amt_and_niit_tables(tables):
    assert amt.exemption_rate(tables, 2027, "Jointly") == D("0.5")
    assert amt.exemption(2_000_000, tables, 2027, "Jointly") == 0
    assert niit.niit_threshold(tables, 2027, "Jointly") == 250_000


def test_2027_full_calculation_runs(tables):
    inputs = FilerInputs(tax_year=2027, filing_status="Single", dob=date(1955, 3, 3),
                         prior_ye_ira_balance=400_000, wages_and_tips=60_000)
    result = compute(inputs, tables)
    assert result.total_tax > 0 and result.warnings != [] and result.tax_year == 2027


def test_amt_ltcg_stacked_vs_flat(tables):
    # Joint: AMTI 240,200 less 140,200 exemption = 100,000 base; 20,000 is gains.
    flat = amt.tentative_tax(240_200, 0, 0, 20_000, tables, 2026, "Jointly", stacked=False)
    stacked = amt.tentative_tax(240_200, 0, 0, 20_000, tables, 2026, "Jointly", stacked=True)
    assert flat == D(80_000) * D("0.26") + D(3_000)
    # 18,900 of gains fill the 0% bracket (to 98,900); the last 1,100 is taxed at 15%
    assert stacked == D(80_000) * D("0.26") + D(165)


def test_amt_ltcg_stacked_all_gains_in_top_bracket(tables):
    # base 700,000 all gains: 0% to 98,900, 15% to 613,700, 20% above
    result = amt.tentative_tax(840_200, 0, 0, 700_000, tables, 2026, "Jointly", stacked=True)
    assert result == (D(613_700) - D(98_900)) * D("0.15") + (D(700_000) - D(613_700)) * D("0.20")


def test_social_security_includes_rmd_unless_legacy(tables):
    inputs = FilerInputs(tax_year=2026, filing_status="Jointly", dob=date(1952, 4, 14),
                         prior_ye_ira_balance=500_000, social_security_benefits=30_000)
    legacy = compute(inputs, tables, legacy=True, as_of_year=2026)
    fixed = compute(inputs, tables)
    assert legacy.taxable_social_security == 0  # workbook leaves the RMD out of provisional income
    expected = (D(500_000) / D("25.5") + D(15_000) - D(32_000)) * D("0.5")
    assert fixed.taxable_social_security == expected
    assert fixed.agi == fixed.rmd + fixed.taxable_social_security
