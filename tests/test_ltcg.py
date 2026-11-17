from decimal import Decimal

from app.calc import ltcg
from app.calc.ordinary import total_tax


def test_golden_bucket_amounts(tables):
    br = ltcg.ltcg_brackets(tables, 2026, "Jointly")
    alloc = ltcg.stacked(Decimal("153096.68627450982"), Decimal("145296.68627450982"), Decimal(7800), br)
    assert [a.amount for a in alloc] == [0, Decimal(7800), 0]
    assert total_tax(alloc) == Decimal(1170)


def test_gains_in_zero_bracket():
    # ordinary 10k, pool 20k, total 30k, 0% bracket up to 98.9k: all gains at 0%
    assert ltcg.bucket_amount(30_000, 10_000, 20_000, 0, 98_900) == 20_000
    assert ltcg.bucket_amount(30_000, 10_000, 20_000, 98_900, 613_700) == 0


def test_gains_split_across_buckets():
    # ordinary 90k, pool 20k: 8.9k fills the 0% bracket, 11.1k lands in 15%
    assert ltcg.bucket_amount(110_000, 90_000, 20_000, 0, 98_900) == Decimal(8_900)
    assert ltcg.bucket_amount(110_000, 90_000, 20_000, 98_900, 613_700) == Decimal(11_100)


def test_standalone_ltcg_tax(tables):
    assert ltcg.ltcg_tax(100_000, tables, 2026, "Jointly") == Decimal(1_100) * Decimal("0.15")


def test_marginal_rate(tables):
    assert ltcg.marginal_rate(50_000, tables, 2026, "Single") == Decimal("0.15")
    assert ltcg.marginal_rate(40_000, tables, 2026, "Single") == 0
    assert ltcg.marginal_rate(10**10, tables, 2026, "Single") is None
