from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest
from pydantic import BaseModel

from app import whatif

D = Decimal


class Inputs(BaseModel):
    long_term_capital_gains: Decimal = D(0)
    short_term_gain_loss: Decimal = D(0)
    schedule_a_deductions: Decimal = D(0)
    ira_conversion: Decimal = D(0)
    qualified_business_income: Decimal = D(0)


def test_adjustments_are_added_to_the_right_inputs():
    base = Inputs(long_term_capital_gains=10_000, short_term_gain_loss=-2_000, schedule_a_deductions=12_000,
                  ira_conversion=5_000)
    adj = whatif.Adjustments(ltcg=D(-4_000), stcg=D(3_000), extra_deductions=D(8_000), extra_ira=D(20_000))
    new = whatif.adjusted_inputs(base, adj)
    assert new.long_term_capital_gains == D(6_000)
    assert new.short_term_gain_loss == D(1_000)
    assert new.schedule_a_deductions == D(20_000)
    assert new.ira_conversion == D(25_000)
    assert base.long_term_capital_gains == D(10_000)  # the original is untouched


def test_blank_inputs_count_as_zero():
    base = SimpleNamespace(long_term_capital_gains=None, short_term_gain_loss=None, schedule_a_deductions=None,
                           ira_conversion=None, model_copy=lambda update: SimpleNamespace(**update))
    new = whatif.adjusted_inputs(base, whatif.Adjustments(ltcg=D(500), extra_deductions=D(700)))
    assert (new.long_term_capital_gains, new.schedule_a_deductions, new.ira_conversion) == (D(500), D(700), D(0))


def test_is_zero_and_income_change():
    assert whatif.Adjustments().is_zero
    adj = whatif.Adjustments(ltcg=D(1_000), stcg=D(-400), extra_deductions=D(9_000), extra_ira=D(2_000))
    assert not adj.is_zero and adj.income_change == D(2_600)  # deductions are not income
    assert not whatif.Adjustments(extra_deductions=D(1)).is_zero


@pytest.mark.parametrize("value,expected", [(D(1200), "+$1,200"), (D(-300), "-$300"), (D("0.4"), "$0"), (D(0), "$0")])
def test_signed_money(value, expected):
    assert whatif.signed_money(value) == expected


def test_signed_points():
    assert whatif.signed_points(D("0.1"), D("0.1125")) == "+1.25 pts"
    assert whatif.signed_points(D("0.12"), D("0.10")) == "-2.00 pts"
    assert whatif.signed_points(D("0.1"), D("0.1")) == "0.00 pts"
    assert whatif.signed_points(None, D("0.1")) == "n/a"


def test_tax_on_the_change():
    base, alt = SimpleNamespace(total_tax=D(1_000)), SimpleNamespace(total_tax=D(1_220))
    assert whatif.tax_on_the_change(base, alt, whatif.Adjustments(extra_ira=D(1_000))) == D("0.22")
    assert whatif.tax_on_the_change(base, alt, whatif.Adjustments(extra_deductions=D(1_000))) is None
    assert whatif.tax_on_the_change(base, alt, whatif.Adjustments()) is None


def fake_result(total_tax, ordinary=60_000, first_bucket=0, agi=100_000, rate="0.22"):
    bracket0 = SimpleNamespace(rate=D(0), limit=D(98_900), unbounded=False)
    bracket_ord = SimpleNamespace(rate=D(rate), limit=D(200_000), unbounded=False)
    return SimpleNamespace(
        total_tax=D(total_tax), due_or_refund=D(total_tax) - D(5_000), effective_rate=D(total_tax) / D(agi), agi=D(agi),
        taxable_social_security=D(0), taxable_ordinary=D(ordinary), taxable_preferential=D(0),
        ordinary_tax=D(total_tax), ltcg_tax=D(0), niit=D(0), amt_owed=D(0),
        ordinary_allocations=[SimpleNamespace(bracket=bracket_ord, amount=D(ordinary))],
        ltcg_allocations=[SimpleNamespace(bracket=bracket0, amount=D(first_bucket))],
        standard_deduction=D(30_000), cash_deduction_limit=D(60_000))


def fake_inputs(schedule_a=0):
    return SimpleNamespace(schedule_a_deductions=D(schedule_a), qualified_business_income=D(0))


def test_comparison_rows_show_current_what_if_and_change():
    rows = {r["Measure"]: r for r in whatif.comparison(fake_result(10_000), fake_inputs(), fake_result(12_200, ordinary=70_000, rate="0.24"), fake_inputs(5_000))}
    assert rows["Total tax"] == {"Measure": "Total tax", "Current": "$10,000", "What-if": "$12,200", "Change": "+$2,200"}
    assert rows["Marginal ordinary rate"]["Current"] == "22%" and rows["Marginal ordinary rate"]["What-if"] == "24%"
    assert rows["Marginal ordinary rate"]["Change"] == "+2.00 pts"
    assert rows["Additional LTCG at 0%"] == {"Measure": "Additional LTCG at 0%", "Current": "$38,900",
                                              "What-if": "$28,900", "Change": "-$10,000"}
    assert rows["Left before Schedule A"]["Current"] == "$30,000" and rows["Left before Schedule A"]["What-if"] == "$25,000"
    assert len(rows) == len(whatif.MEASURES)


def test_comparison_handles_missing_rates_and_rooms():
    base = fake_result(0)
    base.effective_rate = None
    base.ltcg_allocations = []
    rows = {r["Measure"]: r for r in whatif.comparison(base, fake_inputs(), fake_result(100), fake_inputs())}
    assert rows["Effective rate (of AGI)"]["Current"] == "n/a" and rows["Effective rate (of AGI)"]["Change"] == "n/a"
    assert rows["Additional LTCG at 0%"]["Current"] == "n/a" and rows["Additional LTCG at 0%"]["Change"] == "n/a"


def test_the_real_engine_responds_to_each_adjustment(tables):
    from app.calc.engine import compute
    from app.models import FilerInputs

    inputs = FilerInputs(tax_year=2026, filing_status="Single", dob=date(1960, 1, 1), wages_and_tips=50_000)
    base = compute(inputs, tables)

    def run(**kwargs):
        adj = whatif.Adjustments(**{k: D(v) for k, v in kwargs.items()})
        return compute(whatif.adjusted_inputs(inputs, adj), tables)

    ira = run(extra_ira=10_000)
    assert ira.agi - base.agi == D(10_000) and ira.total_tax > base.total_tax
    stcg = run(stcg=5_000)
    assert stcg.agi - base.agi == D(5_000) and stcg.total_tax > base.total_tax
    ltcg = run(ltcg=20_000)
    assert ltcg.agi - base.agi == D(20_000) and ltcg.total_tax >= base.total_tax
    deductions = run(extra_deductions=30_000)
    assert deductions.agi == base.agi and deductions.total_tax < base.total_tax
    assert run().total_tax == base.total_tax  # no adjustment, no change
