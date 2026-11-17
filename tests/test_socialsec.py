from decimal import Decimal

from app.calc.socialsec import taxable_ss


def test_zero_benefits(tables):
    assert taxable_ss(0, 151_300, "Jointly", tables, 2026) == 0


def test_joint_two_tiers(tables):
    # combined 55,000; excess 23,000; tier1 12,000 (50%) + tier2 11,000 (85%) = 15,350
    assert taxable_ss(30_000, 40_000, "Jointly", tables, 2026) == Decimal(15_350)


def test_single_first_tier_only(tables):
    # combined 30,000; excess 5,000 at 50% = 2,500
    assert taxable_ss(20_000, 20_000, "Single", tables, 2026) == Decimal(2_500)


def test_cap_at_85_percent(tables):
    assert taxable_ss(10_000, 500_000, "Single", tables, 2026) == Decimal(8_500)


def test_below_base_is_zero(tables):
    assert taxable_ss(10_000, 15_000, "Single", tables, 2026) == 0


def test_separate_not_lived_apart_has_zero_base(tables):
    assert taxable_ss(10_000, 0, "Separate", tables, 2026, mfs_lived_apart=False) == Decimal(4_250)
