"""Taxable Social Security benefits (50% / 85% tiers)."""
from __future__ import annotations

from decimal import Decimal

from app.calc.common import ZERO, dec, get_param
from app.tables import Tables

HALF = Decimal("0.5")
EIGHTY_FIVE = Decimal("0.85")


def taxable_ss(ssi, other_income, status: str, tables: Tables, year: int,
               mfs_lived_apart: bool = True) -> Decimal:
    """SS_Taxable. ``status`` must already be normalized (Single/Jointly/Separate)."""
    ssi, other = dec(ssi), dec(other_income)
    base1 = get_param(tables, year, "SS_Base1", status)
    base2 = get_param(tables, year, "SS_Base2", status)
    if status == "Separate" and not mfs_lived_apart:
        base1 = base2 = ZERO
    combined = other + HALF * ssi
    if combined <= base1:
        return ZERO
    excess = combined - base1
    width = base2 - base1
    tier1 = min(excess, width)
    tier2 = max(ZERO, excess - width)
    return min(HALF * tier1 + EIGHTY_FIVE * tier2, EIGHTY_FIVE * ssi)
