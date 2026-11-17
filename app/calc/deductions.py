"""Standard deduction: base plus age-65 add-on and senior bonus."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.calc.common import ZERO, MissingDataError, dec, get_param, round_half_up
from app.tables import Tables


def base_standard_deduction(tables: Tables, year: int, status: str) -> Decimal:
    for row in tables.rows("tblStandDeductionBase"):
        if row.FilingYear == year and row.Status == status:
            return row.Amount
    raise MissingDataError(f"tblStandDeductionBase has no {status} row for {year}")


def is_65_plus(dob: date, as_of_year: int) -> bool:
    """Age 65 during the year; a Jan 1 birthday counts one year earlier."""
    offset = 64 if (dob.month == 1 and dob.day == 1) else 65
    return as_of_year >= dob.year + offset


def standard_deduction_basic(dob: date, status: str, base, as_of_year: int,
                             tables: Tables, param_year: int) -> Decimal:
    """StandardDeduction_Basic: base plus the age-65 add-on for one filer."""
    add_on = get_param(tables, param_year, "AgeAddOn65", status)
    return dec(base) + (add_on if is_65_plus(dob, as_of_year) else ZERO)


def standard_deduction_full(dob: date, status: str, base, agi, as_of_year: int,
                            tables: Tables, param_year: int,
                            spouse_dob: date | None = None) -> Decimal:
    """StandardDeduction_Full: base + age add-on(s) + phased-out senior bonus."""
    single = status == "Single"
    first = is_65_plus(dob, as_of_year)
    second = spouse_dob is not None and is_65_plus(spouse_dob, as_of_year)
    qualifying = int(first) + int(second)

    per_person = get_param(tables, param_year, "AgeAddOn65", status)
    add_on = per_person * (int(first) if single else qualifying)

    bonus_per = get_param(tables, param_year, "SeniorBonusPerPerson", status)
    start = get_param(tables, param_year, "SeniorBonusPhaseoutStart", status)
    rate = get_param(tables, param_year, "SeniorBonusPhaseoutRate", status)
    if qualifying == 0:
        bonus = ZERO
    else:
        bonus = max(ZERO, bonus_per * qualifying - max(ZERO, dec(agi) - start) * rate)
    return dec(base) + add_on + round_half_up(bonus)
