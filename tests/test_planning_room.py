from decimal import Decimal
from types import SimpleNamespace

from app import report

D = Decimal


def allocation(rate, limit, amount, unbounded=False):
    return SimpleNamespace(bracket=SimpleNamespace(rate=D(rate), limit=D(limit), unbounded=unbounded), amount=D(amount))


def result(ordinary, ltcg_allocations, **extra):
    return SimpleNamespace(taxable_ordinary=D(ordinary), ltcg_allocations=ltcg_allocations, **extra)


def ltcg_rows(first_amount=0):
    return [allocation("0", 98_900, first_amount), allocation("0.15", 613_700, 0), allocation("0.20", 9_999_999, 0, True)]


def test_room_is_the_zero_bracket_less_ordinary_income_and_gains_already_in_it():
    room, top = report.zero_ltcg_room(result(60_000, ltcg_rows(10_000)))
    assert (room, top) == (D(28_900), D(98_900))


def test_room_with_no_gains_at_all():
    assert report.zero_ltcg_room(result(40_000, ltcg_rows(0))) == (D(58_900), D(98_900))


def test_room_is_zero_when_ordinary_income_fills_the_bracket():
    assert report.zero_ltcg_room(result(145_296, ltcg_rows(0))) == (D(0), D(98_900))


def test_room_is_zero_when_gains_fill_the_bracket():
    assert report.zero_ltcg_room(result(60_000, ltcg_rows(38_900))) == (D(0), D(98_900))


def test_room_is_none_without_a_finite_zero_bracket():
    assert report.zero_ltcg_room(result(0, [allocation("0.15", 100, 0)])) == (None, None)
    assert report.zero_ltcg_room(result(0, [allocation("0", 9_999_999, 0, True)])) == (None, None)
    assert report.zero_ltcg_room(result(0, [])) == (None, None)


def inputs(schedule_a=0, qbi=0):
    return SimpleNamespace(schedule_a_deductions=schedule_a, qualified_business_income=qbi)


def deduction_result(standard=37_419, cash_limit=114_309):
    return SimpleNamespace(standard_deduction=D(standard), cash_deduction_limit=D(cash_limit))


def test_gap_is_the_standard_deduction_less_schedule_a():
    assert report.itemizing_gap(deduction_result(), inputs(12_000)) == D(25_419)


def test_gap_counts_qualified_business_income_like_the_engine_does():
    assert report.itemizing_gap(deduction_result(), inputs(12_000, 5_000)) == D(20_419)


def test_gap_is_zero_once_itemizing_wins():
    assert report.itemizing_gap(deduction_result(), inputs(40_000)) == D(0)
    assert report.itemizing_gap(deduction_result(), inputs(37_419)) == D(0)


def test_gap_respects_the_agi_cash_limit_and_blank_amounts():
    assert report.itemizing_gap(deduction_result(cash_limit=10_000), inputs(30_000)) == D(27_419)
    assert report.itemizing_gap(deduction_result(), inputs(None, None)) == D(37_419)
