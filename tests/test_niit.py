from decimal import Decimal

import pytest

from app.calc import niit
from app.calc.common import MissingDataError


def test_threshold_lookup(tables):
    assert niit.niit_threshold(tables, 2026, "Jointly") == 250_000
    assert niit.niit_threshold(tables, 2025, "Single") == 200_000
    with pytest.raises(MissingDataError):
        niit.niit_threshold(tables, 2024, "Single")


def test_below_threshold_is_zero(tables):
    assert niit.niit_tax(190_515, 6_300, tables, 2026, "Jointly") == 0


def test_taxed_on_lesser_of_nii_and_excess(tables):
    assert niit.niit_tax(300_000, 100_000, tables, 2026, "Jointly") == Decimal(50_000) * Decimal("0.038")
    assert niit.niit_tax(400_000, 20_000, tables, 2026, "Jointly") == Decimal(20_000) * Decimal("0.038")


def test_negative_nii_clamped_unless_legacy(tables):
    assert niit.niit_tax(300_000, -10_000, tables, 2026, "Jointly") == 0
    assert niit.niit_tax(300_000, -10_000, tables, 2026, "Jointly", clamp_nii=False) == Decimal(-380)


def test_buildup():
    assert niit.nii_buildup(900, 2400, 3000) == Decimal(6300)
