"""Format a TaxResult for display (no Streamlit import, so it is testable)."""
from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.calc.engine import TaxResult
    from app.models import FilerInputs


def fmt_money(value: Decimal) -> str:
    rounded = int(value.quantize(Decimal(1)))
    return f"-${-rounded:,}" if rounded < 0 else f"${rounded:,}"


def fmt_rate(value: Decimal | None, places: int = 2) -> str:
    return "n/a" if value is None else f"{value * 100:.{places}f}%"


def due_label(result: TaxResult) -> str:
    return "Refund" if result.due_or_refund < 0 else "Amount due"


def marginal_ordinary_rate(result: TaxResult) -> Decimal | None:
    """Rate of the highest ordinary bracket that holds any income (None if there is none)."""
    for allocation in reversed(result.ordinary_allocations):
        if allocation.amount > 0:
            return allocation.bracket.rate
    return None


def zero_ltcg_room(result: TaxResult) -> tuple[Decimal | None, Decimal | None]:
    """(more long-term gains that still fit in the 0% bracket, top of the 0% bracket).

    Gains stack on top of taxable ordinary income, so the room is the 0% ceiling less the taxable
    ordinary income and less the gains already placed in that bracket. Both values are None when
    the tables have no finite 0% bracket.
    """
    for allocation in result.ltcg_allocations:
        bracket = allocation.bracket
        if bracket.rate == 0:
            if bracket.unbounded:
                return None, None
            room = bracket.limit - max(result.taxable_ordinary, Decimal(0)) - allocation.amount
            return max(room, Decimal(0)), bracket.limit
    return None, None


def itemizing_gap(result: TaxResult, inputs: FilerInputs) -> Decimal:
    """More Schedule A deductions that fit before itemizing beats the standard deduction.

    Mirrors the engine: itemized = Schedule A + qualified business income, limited to the AGI cash
    limit, and compared with the standard deduction. Zero once itemizing already wins.
    """
    itemized = Decimal(str(inputs.schedule_a_deductions or 0)) + Decimal(str(inputs.qualified_business_income or 0))
    counted = min(itemized, result.cash_deduction_limit)
    return max(result.standard_deduction - counted, Decimal(0))


def sections(r: TaxResult) -> list[tuple[str, list[tuple[str, str]]]]:
    """Result figures grouped like the workbook's sections: (title, [(label, value)])."""
    return [
        ("Income", [
            ("Required minimum distribution", fmt_money(r.rmd)),
            ("Taxable Social Security", fmt_money(r.taxable_social_security)),
            ("Adjusted gross income", fmt_money(r.agi)),
            ("Ordinary income", fmt_money(r.ordinary_income)),
            ("Preferential income (LTCG + qualified dividends)", fmt_money(r.preferential_subtotal)),
        ]),
        ("Deductions", [
            ("Standard deduction", fmt_money(r.standard_deduction)),
            ("Applicable deduction", fmt_money(r.applicable_deduction)),
            ("Adjusted taxable income", fmt_money(r.adjusted_taxable_income)),
            ("Taxable ordinary income", fmt_money(r.taxable_ordinary)),
            ("Taxable preferential income", fmt_money(r.taxable_preferential)),
        ]),
        ("Tax", [
            ("Ordinary income tax", fmt_money(r.ordinary_tax)),
            ("Long-term capital gains tax", fmt_money(r.ltcg_tax)),
            ("Regular tax", fmt_money(r.regular_tax)),
            ("Net investment income", fmt_money(r.net_investment_income)),
            ("NIIT threshold", fmt_money(r.niit_threshold)),
            ("Net investment income tax", fmt_money(r.niit)),
        ]),
        ("Alternative minimum tax", [
            ("SALT cap", fmt_money(r.salt_cap)),
            ("SALT addback", fmt_money(r.salt_addback)),
            ("Exemption phase-out rate", fmt_rate(r.amt_exemption_rate, 1)),
            ("AMT exemption", fmt_money(r.amt_exemption)),
            ("Tentative minimum tax", fmt_money(r.amt_tentative)),
            ("AMT owed", fmt_money(r.amt_owed)),
        ]),
        ("Summary", [
            ("Total tax", fmt_money(r.total_tax)),
            ("Tax paid", fmt_money(r.tax_paid)),
            (due_label(r), fmt_money(abs(r.due_or_refund))),
            ("Effective rate (of AGI)", fmt_rate(r.effective_rate)),
        ]),
    ]


def allocation_records(allocations: list) -> list[dict]:
    """Rows for a bracket table: bucket, rate, upper limit, income in bracket, tax."""
    records = []
    for a in allocations:
        b = a.bracket
        records.append({
            "Bucket": b.bucket,
            "Rate": fmt_rate(b.rate, 0),
            "Up to": "No limit" if b.unbounded else fmt_money(b.limit),
            "Income in bracket": fmt_money(a.amount),
            "Tax": fmt_money(a.tax),
        })
    return records
