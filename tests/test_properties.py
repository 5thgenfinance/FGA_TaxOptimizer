"""Property tests (need hypothesis; skipped if it is not installed)."""
import pytest

pytest.importorskip("hypothesis")
from hypothesis import given, strategies as st  # noqa: E402

from app.calc import ordinary  # noqa: E402
from app.tables import load_all  # noqa: E402

TABLES = load_all()
BRACKETS = ordinary.get_brackets(TABLES, "tblTaxRate", 2026, "Single")


@given(st.integers(0, 640_600), st.integers(0, 640_600))
def test_tax_is_monotonic(a, b):
    lo, hi = sorted((a, b))
    assert ordinary.total_tax(ordinary.allocate(lo, BRACKETS)) <= ordinary.total_tax(ordinary.allocate(hi, BRACKETS))


@given(st.integers(0, 640_600))
def test_allocation_sums_to_income(income):
    assert sum(a.amount for a in ordinary.allocate(income, BRACKETS)) == income
