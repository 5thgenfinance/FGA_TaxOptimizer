from decimal import Decimal

import pytest

from app.calc import ordinary
from app.calc.common import MissingDataError


def test_golden_allocation(tables):
    br = ordinary.get_brackets(tables, "tblTaxRate", 2026, "Jointly")
    alloc = ordinary.allocate(Decimal("145296.68627450982"), br)
    assert [a.amount for a in alloc[:2]] == [Decimal(24800), Decimal(76000)]
    assert round(ordinary.total_tax(alloc), 2) == Decimal("21389.27")


def test_brackets_have_lower_bounds(tables):
    br = ordinary.get_brackets(tables, "tblTaxRate", 2026, "Single")
    assert br[0].lower == 0 and br[1].lower == br[0].limit


def test_exactly_at_limit(tables):
    assert ordinary.income_tax(12400, tables, 2026, "Single") == Decimal(12400) * Decimal("0.10")


def test_seven_buckets_in_2025(tables):
    assert len(ordinary.get_brackets(tables, "tblTaxRate", 2025, "Single")) == 7


def test_separate_not_supported(tables):
    with pytest.raises(MissingDataError):
        ordinary.get_brackets(tables, "tblTaxRate", 2026, "Separate")


def test_exceeds_top_bracket_flag(tables):
    br = ordinary.get_brackets(tables, "tblTaxRate", 2026, "Single")
    assert ordinary.exceeds_top_bracket(700_000, br)
    assert not ordinary.exceeds_top_bracket(600_000, br)
