"""Net investment income tax."""
from __future__ import annotations

from decimal import Decimal

from app.calc.common import ZERO, MissingDataError, dec, get_param
from app.tables import Tables


def niit_threshold(tables: Tables, year: int, status: str) -> Decimal:
    for row in tables.rows("tblNIIT"):
        if row.Year == year and row.Status == status:
            return row.Threshold
    raise MissingDataError(f"tblNIIT has no {status} row for {year}")


def nii_buildup(taxable_interest, ordinary_dividends, total_cap_gain, other_passive=0) -> Decimal:
    return dec(taxable_interest) + dec(ordinary_dividends) + dec(total_cap_gain) + dec(other_passive)


def niit_tax(magi, nii, tables: Tables, year: int, status: str, clamp_nii: bool = True) -> Decimal:
    """3.8% x min(NII, MAGI over threshold). ``clamp_nii=False`` reproduces the
    workbook, where negative NII yields a negative tax."""
    threshold = niit_threshold(tables, year, status)
    rate = get_param(tables, year, "NIIT_Rate", status)
    base = min(dec(nii), max(ZERO, dec(magi) - threshold))
    if clamp_nii:
        base = max(ZERO, base)
    return base * rate
