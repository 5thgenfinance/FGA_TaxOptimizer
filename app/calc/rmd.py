"""Required minimum distributions (Uniform Lifetime Table)."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.calc.common import ZERO, MissingDataError, dec
from app.tables import Tables


def start_age(dob: date, tables: Tables) -> int:
    """RMD start age by birth year, from tblRMDStartAge.csv."""
    age = None
    for row in tables.rows("tblRMDStartAge"):
        if row.BirthYearFrom <= dob.year:
            age = row.StartAge
    if age is None:
        raise MissingDataError(f"tblRMDStartAge has no row for birth year {dob.year}")
    return age


def divisor(age: int, tables: Tables) -> Decimal:
    for row in tables.rows("tblUniformRMDFactors"):
        if row.Age == age:
            return row.LifeExpectancyFactor
    raise MissingDataError(f"tblUniformRMDFactors has no factor for age {age}")


def calc_rmd(dob: date, calc_year: int, prior_year_end_balance, tables: Tables) -> Decimal:
    """Minimum withdrawal: 0 before the start age, else balance / divisor."""
    balance = dec(prior_year_end_balance)
    if balance < 0:
        raise ValueError("prior_year_end_balance must be non-negative")
    age = calc_year - dob.year
    if age < start_age(dob, tables):
        return ZERO
    return balance / divisor(age, tables)
