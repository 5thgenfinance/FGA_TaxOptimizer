from decimal import Decimal
from types import SimpleNamespace

from app import report


def allocation(rate, amount):
    return SimpleNamespace(amount=Decimal(amount), bracket=SimpleNamespace(rate=Decimal(rate)))


def test_marginal_rate_is_the_highest_bracket_with_income():
    result = SimpleNamespace(ordinary_allocations=[
        allocation("0.10", 24_800), allocation("0.12", 76_000), allocation("0.22", 44_496), allocation("0.24", 0)])
    assert report.marginal_ordinary_rate(result) == Decimal("0.22")


def test_marginal_rate_is_none_without_income():
    result = SimpleNamespace(ordinary_allocations=[allocation("0.10", 0), allocation("0.12", 0)])
    assert report.marginal_ordinary_rate(result) is None
    assert report.marginal_ordinary_rate(SimpleNamespace(ordinary_allocations=[])) is None
