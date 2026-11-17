"""Long-term capital gains / preferential income tax."""
from __future__ import annotations

from decimal import Decimal

from app.calc.common import ZERO, dec
from app.calc.ordinary import Allocation, Bracket, allocate, get_brackets, total_tax
from app.tables import Tables


def bucket_amount(taxable_income, ordinary_income, pool, floor, ceiling) -> Decimal:
    """LTCG_Bucket_Amount: preferential income that falls inside one bracket."""
    t, o, p = dec(taxable_income), dec(ordinary_income), dec(pool)
    floor, ceiling = dec(floor), dec(ceiling)
    ceiling_cap = min(t, ceiling)
    ordinary_below_ceiling = max(o, floor)
    room = max(ZERO, ceiling_cap - ordinary_below_ceiling)
    pool_remaining = max(ZERO, p - max(ZERO, floor - o))
    return max(ZERO, min(room, pool_remaining))


def stacked(taxable_income, taxable_ordinary, pool, brackets: list[Bracket]) -> list[Allocation]:
    """Allocate the preferential pool across LTCG brackets, stacked above ordinary income."""
    out = []
    for b in brackets:
        amount = bucket_amount(taxable_income, taxable_ordinary, pool, b.lower, b.limit)
        out.append(Allocation(b, amount, amount * b.rate))
    return out


def ltcg_brackets(tables: Tables, year: int, status: str) -> list[Bracket]:
    return get_brackets(tables, "tblTaxRateLTCG", year, status)


def ltcg_tax(taxable, tables: Tables, year: int, status: str) -> Decimal:
    """Stand-alone LTCGTax (not stacked on ordinary income), year-filtered."""
    return total_tax(allocate(taxable, ltcg_brackets(tables, year, status)))


def marginal_rate(taxable, tables: Tables, year: int, status: str) -> Decimal | None:
    """LTCG_Rate: rate of the first bracket whose limit is >= income; None if none match."""
    t = dec(taxable)
    for b in ltcg_brackets(tables, year, status):
        if t <= b.limit:
            return b.rate
    return None
