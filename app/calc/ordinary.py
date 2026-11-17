"""Ordinary income tax: bracket lookup and allocation (TaxRate, IncomeTax)."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.calc.common import ZERO, MissingDataError, dec
from app.tables import Tables, is_unbounded


@dataclass(frozen=True)
class Bracket:
    bucket: int
    lower: Decimal
    limit: Decimal
    rate: Decimal

    @property
    def width(self) -> Decimal:
        return self.limit - self.lower

    @property
    def unbounded(self) -> bool:
        return is_unbounded(self.limit)


@dataclass(frozen=True)
class Allocation:
    bracket: Bracket
    amount: Decimal
    tax: Decimal


def get_brackets(tables: Tables, table: str, year: int, status: str) -> list[Bracket]:
    """Brackets for one year and status, in bucket order (TaxRate / TaxRateLTCG)."""
    if status not in ("Single", "Jointly"):
        raise MissingDataError(f"{table} has no limits for status {status!r}")
    rows = [r for r in tables.rows(table) if r.Year == year]
    if not rows:
        raise MissingDataError(f"{table} has no rows for {year}")
    out, lower = [], ZERO
    for r in rows:
        limit = getattr(r, status)
        out.append(Bracket(r.Bucket, lower, limit, r.Rate))
        lower = limit
    return out


def allocate(taxable, brackets: list[Bracket]) -> list[Allocation]:
    """Spread taxable income across brackets: max(0, min(T, limit) - lower) x rate."""
    t = max(dec(taxable), ZERO)
    result = []
    for b in brackets:
        amount = max(ZERO, min(t, b.limit) - b.lower)
        result.append(Allocation(b, amount, amount * b.rate))
    return result


def total_tax(allocations: list[Allocation]) -> Decimal:
    return sum((a.tax for a in allocations), ZERO)


def exceeds_top_bracket(taxable, brackets: list[Bracket]) -> bool:
    """True when income is above a finite (non-sentinel) top bracket."""
    top = brackets[-1]
    return (not top.unbounded) and dec(taxable) > top.limit


def income_tax(taxable, tables: Tables, year: int, status: str) -> Decimal:
    """IncomeTax with year-filtered arrays (documented fix, spec section 7.1)."""
    return total_tax(allocate(taxable, get_brackets(tables, "tblTaxRate", year, status)))
