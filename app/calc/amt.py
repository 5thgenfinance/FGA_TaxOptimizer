"""Alternative minimum tax (simplified, as in the workbook)."""
from __future__ import annotations

from decimal import Decimal

from app.calc.common import ZERO, MissingDataError, dec, get_param
from app.tables import Tables


def _row(tables: Tables, year: int, status: str):
    for row in tables.rows("tblAMT"):
        if row.Year == year and row.Status == status:
            return row
    raise MissingDataError(f"tblAMT has no {status} row for {year}")


def salt_cap(tables: Tables, year: int, status: str) -> Decimal:
    return _row(tables, year, status).SaltCap


def salt_addback(schedule_a_salt, cap: Decimal, legacy: bool) -> Decimal:
    """Legacy: a blank SALT input yields the full cap (MIN ignores blank cells).
    Otherwise a blank input is treated as zero."""
    if schedule_a_salt is None:
        return cap if legacy else ZERO
    return min(dec(schedule_a_salt), cap)


def exemption_rate(tables: Tables, year: int, status: str) -> Decimal:
    row = _row(tables, year, status)
    return row.Exemption / (row.End - row.Start)


def exemption(amti, tables: Tables, year: int, status: str) -> Decimal:
    row = _row(tables, year, status)
    reduction = max(ZERO, (dec(amti) - row.Start) * exemption_rate(tables, year, status))
    return max(ZERO, row.Exemption - reduction)


def tentative_tax(regular_taxable_income, salt_add, other_preferences, ltcg_pool,
                  tables: Tables, year: int, status: str) -> Decimal:
    """AMT_Tax: 26%/28% on the ordinary part plus a flat rate on the LTCG pool."""
    row = _row(tables, year, status)
    amti = dec(regular_taxable_income) + dec(salt_add) + dec(other_preferences)
    base = max(ZERO, amti - exemption(amti, tables, year, status))
    pool = dec(ltcg_pool)
    ordinary_part = max(ZERO, base - pool)
    ltcg_part = min(base, pool)
    if ordinary_part <= row.Breakpoint:
        ordinary_tax = ordinary_part * row.Lower
    else:
        ordinary_tax = row.Breakpoint * row.Lower + (ordinary_part - row.Breakpoint) * row.Upper
    return ordinary_tax + ltcg_part * get_param(tables, year, "AMT_LTCG_FlatRate", status)


def amt_owed(regular_taxable_income, salt_add, other_preferences, ltcg_pool,
             tables: Tables, year: int, status: str, regular_tax) -> Decimal:
    tentative = tentative_tax(regular_taxable_income, salt_add, other_preferences,
                              ltcg_pool, tables, year, status)
    return max(ZERO, tentative - dec(regular_tax))
