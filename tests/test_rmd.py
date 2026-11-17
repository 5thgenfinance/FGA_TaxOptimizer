from datetime import date
from decimal import Decimal

import pytest

from app.calc.common import MissingDataError
from app.calc.rmd import calc_rmd, start_age


def test_golden_rmd(tables):
    assert calc_rmd(date(1952, 4, 14), 2026, 1_000_000, tables) == Decimal(1_000_000) / Decimal("25.5")


@pytest.mark.parametrize("year,expected", [(1950, 72), (1951, 73), (1959, 73), (1960, 75), (1975, 75)])
def test_start_age_by_birth_year(tables, year, expected):
    assert start_age(date(year, 6, 1), tables) == expected


def test_zero_before_start_age(tables):
    assert calc_rmd(date(1960, 1, 1), 2026, 500_000, tables) == 0


def test_age_72_uses_the_irs_divisor(tables):
    assert calc_rmd(date(1950, 6, 1), 2022, 274_000, tables) == Decimal(10_000)


def test_oldest_ages_have_factors(tables):
    assert calc_rmd(date(1906, 1, 1), 2026, 200, tables) == Decimal(100)  # age 120, divisor 2.0


def test_age_beyond_table_raises(tables):
    with pytest.raises(MissingDataError):
        calc_rmd(date(1900, 6, 1), 2026, 100_000, tables)  # age 126


def test_negative_balance_rejected(tables):
    with pytest.raises(ValueError):
        calc_rmd(date(1952, 4, 14), 2026, -1, tables)
