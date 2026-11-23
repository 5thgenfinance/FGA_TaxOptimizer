"""2025 data: IRS Rev. Proc. 2024-40, the Form 6251 instructions, and the 2025 return that was filed."""
from datetime import date
from decimal import Decimal

import pytest

from app.calc import amt, deductions, ltcg, niit, ordinary
from app.calc.engine import compute
from app.models import FilerInputs

D = Decimal


def test_2025_is_a_supported_year(tables):
    assert 2025 in tables.supported_years()


@pytest.mark.parametrize("income,tax", [
    (11_925, "1192.50"), (48_475, "5578.50"), (103_350, "17651.00"),
    (197_300, "40199.00"), (250_525, "57231.00"), (626_350, "188769.75"),
])
def test_2025_single_tax_at_each_bracket_top(tables, income, tax):
    assert ordinary.income_tax(income, tables, 2025, "Single") == D(tax)


@pytest.mark.parametrize("income,tax", [
    (23_850, "2385.00"), (96_950, "11157.00"), (206_700, "35302.00"),
    (394_600, "80398.00"), (501_050, "114462.00"), (751_600, "202154.50"),
])
def test_2025_joint_tax_at_each_bracket_top(tables, income, tax):
    assert ordinary.income_tax(income, tables, 2025, "Jointly") == D(tax)


def test_2025_ltcg_thresholds(tables):
    single = ltcg.ltcg_brackets(tables, 2025, "Single")
    joint = ltcg.ltcg_brackets(tables, 2025, "Jointly")
    assert [b.limit for b in single[:2]] == [D(48_350), D(533_400)]
    assert [b.limit for b in joint[:2]] == [D(96_700), D(600_050)]


def test_2025_amt_exemption_phases_out_at_25_percent(tables):
    for status in ("Single", "Jointly", "Separate"):
        assert amt.exemption_rate(tables, 2025, status) == D("0.25")
    assert amt.exemption(978_750, tables, 2025, "Single") == 0
    assert amt.exemption(1_800_700, tables, 2025, "Jointly") == 0
    assert amt.exemption(626_350, tables, 2025, "Single") == D(88_100)
    assert amt.exemption(1_252_700, tables, 2025, "Jointly") == D(137_000)


def test_2025_amt_rate_breakpoint_and_salt_cap(tables):
    rows = {(r.Year, r.Status): r for r in tables.rows("tblAMT")}
    assert rows[(2025, "Single")].Breakpoint == D(239_100)
    assert rows[(2025, "Separate")].Breakpoint == D(119_550)
    assert amt.salt_cap(tables, 2025, "Single") == D(40_000)
    assert amt.salt_cap(tables, 2025, "Separate") == D(20_000)


def test_2025_niit_thresholds(tables):
    assert niit.niit_threshold(tables, 2025, "Single") == 200_000
    assert niit.niit_threshold(tables, 2025, "Jointly") == 250_000


def test_2025_standard_deduction_for_seniors(tables):
    # single, 65 or older: 15,750 + 2,000 add-on + 6,000 senior deduction (AGI under 75,000)
    single = deductions.standard_deduction_full(date(1950, 5, 1), "Single", 15_750, 60_000, 2025, tables, 2025)
    assert single == D(15_750 + 2_000 + 6_000)
    # joint, both 65 or older: 31,500 + 2 x 1,600 + 12,000 (AGI under 150,000)
    joint = deductions.standard_deduction_full(date(1950, 5, 1), "Jointly", 31_500, 100_000, 2025, tables, 2025,
                                               date(1950, 5, 1))
    assert joint == D(31_500 + 3_200 + 12_000)


def test_the_filed_2025_return_is_reproduced(tables):
    """Form 1040-SR for 2025 (single, itemizing). The date of birth is not on the return; any date before
    1961-01-02 gives the same answer because itemized deductions are far above the standard deduction.
    The return's tax is 7,500 on line 16. Its 170 foreign tax credit is not modeled by the app."""
    inputs = FilerInputs(
        tax_year=2025, filing_status="Single", dob=date(1955, 6, 15),
        social_security_benefits=39_143, ira_conversion=57_620, qualified_dividends=2_778,
        taxable_interest=1_615, ordinary_dividends=4_425, additional_income=5_192,
        short_term_gain_loss=5_302, long_term_capital_gains=83_932,
        schedule_a_deductions=96_622, qualified_business_income=1_039, schedule_a_salt=51,
        tax_withheld=7_313,
    )
    result = compute(inputs, tables)
    assert round(result.taxable_social_security) == 33_272  # 85% of benefits
    assert round(result.agi) == 191_358
    assert round(result.applicable_deduction) == 97_661
    assert round(result.adjusted_taxable_income) == 93_697
    assert round(result.taxable_ordinary) == 6_987
    assert round(result.taxable_preferential) == 86_710
    assert abs(result.regular_tax - D(7_500)) <= D("1.5")
    assert result.niit == 0 and result.amt_owed == 0
