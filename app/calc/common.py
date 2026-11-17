"""Shared helpers and errors for the calculation modules."""
from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from app.tables import Tables

ZERO = Decimal(0)
ONE = Decimal(1)


class CalcError(Exception):
    """Base class for calculation errors."""


class MissingDataError(CalcError):
    """A table has no row for the requested year, status or age."""


class UnknownStatusError(CalcError):
    """A filing status string is not in tblStatusAliases."""


def dec(value) -> Decimal:
    """Convert None/int/float/str to Decimal (None -> 0)."""
    if value is None:
        return ZERO
    return value if isinstance(value, Decimal) else Decimal(str(value))


def round_half_up(value: Decimal) -> Decimal:
    """Excel ROUND(x, 0) for the non-negative values used here."""
    return value.quantize(ONE, rounding=ROUND_HALF_UP)


def get_param(tables: Tables, year: int, key: str, status: str) -> Decimal:
    """Look up a tblParameters value for (year, key) in the status column."""
    for row in tables.rows("tblParameters"):
        if row.Year == year and row.Key == key:
            return getattr(row, status)
    raise MissingDataError(f"tblParameters has no {key} for {year}")
