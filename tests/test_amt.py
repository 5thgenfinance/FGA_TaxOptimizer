from decimal import Decimal

from app.calc import amt


def test_golden_amt(tables):
    ati = Decimal("153096.68627450982")
    assert amt.exemption_rate(tables, 2026, "Jointly") == Decimal("0.5")
    assert amt.exemption(ati + 40_400, tables, 2026, "Jointly") == Decimal(140_200)
    tentative = amt.tentative_tax(ati, 40_400, 0, 7_800, tables, 2026, "Jointly")
    assert round(tentative, 2) == Decimal("12999.14")
    assert amt.amt_owed(ati, 40_400, 0, 7_800, tables, 2026, "Jointly", Decimal("22559.27098")) == 0


def test_exemption_phaseout(tables):
    # Jointly start 1,000,000, rate 0.5: AMTI 1,100,000 reduces exemption by 50,000
    assert amt.exemption(1_100_000, tables, 2026, "Jointly") == Decimal(90_200)


def test_upper_rate_above_breakpoint(tables):
    # Single, exemption 90,100. AMTI 400,000 -> base 309,900; 244,500@26% + 65,400@28%
    expected = Decimal(244_500) * Decimal("0.26") + Decimal(65_400) * Decimal("0.28")
    assert amt.tentative_tax(400_000, 0, 0, 0, tables, 2026, "Single") == expected


def test_salt_addback_modes(tables):
    cap = amt.salt_cap(tables, 2026, "Jointly")
    assert cap == 40_400
    assert amt.salt_addback(None, cap, legacy=True) == cap
    assert amt.salt_addback(None, cap, legacy=False) == 0
    assert amt.salt_addback(10_000, cap, legacy=True) == 10_000
    assert amt.salt_addback(99_999, cap, legacy=False) == cap
