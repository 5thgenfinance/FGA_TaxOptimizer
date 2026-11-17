from datetime import date
from decimal import Decimal

from app.calc import deductions as d


def test_golden_full_deduction(tables):
    result = d.standard_deduction_full(date(1952, 4, 14), "Jointly", 32200, Decimal("190515.68627450982"),
                                       2026, tables, 2026, date(1974, 9, 30))
    assert result == Decimal(37419)


def test_under_65_gets_base_only(tables):
    assert d.standard_deduction_full(date(1980, 5, 1), "Single", 16100, 100_000, 2026, tables, 2026) == 16100


def test_single_65_plus_bonus_phaseout(tables):
    # base 16100 + add-on 2050 + bonus max(0, 6000 - (100000-75000)*0.06 = 1500) = 4500
    assert d.standard_deduction_full(date(1950, 5, 1), "Single", 16100, 100_000, 2026, tables, 2026) == 16100 + 2050 + 4500


def test_bonus_fully_phased_out(tables):
    assert d.standard_deduction_full(date(1950, 5, 1), "Single", 16100, 200_000, 2026, tables, 2026) == 16100 + 2050


def test_january_first_birthday_rule():
    assert d.is_65_plus(date(1961, 1, 1), 2025)
    assert not d.is_65_plus(date(1961, 1, 2), 2025)
    assert d.is_65_plus(date(1961, 1, 2), 2026)


def test_basic_variant(tables):
    assert d.standard_deduction_basic(date(1950, 1, 1), "Jointly", 32200, 2026, tables, 2026) == 32200 + 1650
    assert d.standard_deduction_basic(date(1990, 1, 1), "Jointly", 32200, 2026, tables, 2026) == 32200
