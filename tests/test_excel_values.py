from datetime import date, datetime

import pytest

from app.excel_values import to_json_value


class WinDateTime(datetime):
    """Stand-in for pywin32's datetime subclass."""


def convert(value, kind):
    problems = []
    return to_json_value("inpX", value, kind, problems), problems


@pytest.mark.parametrize("value", [None, "", "   "])
def test_blank_cells_are_null(value):
    assert convert(value, "money") == (None, [])
    assert convert(value, "date") == (None, [])


def test_dates_from_datetimes_dates_and_serials():
    assert convert(datetime(1952, 4, 14, 0, 0), "date") == ("1952-04-14", [])
    assert convert(WinDateTime(1952, 4, 14), "date") == ("1952-04-14", [])
    assert convert(date(1952, 4, 14), "date") == ("1952-04-14", [])
    serial = float((date(1952, 4, 14) - date(1899, 12, 30)).days)  # Excel serial number
    assert convert(serial, "date") == ("1952-04-14", [])


def test_numbers():
    assert convert(2026.0, "int") == (2026, [])
    assert convert(1_000_000.0, "money") == (1_000_000, [])
    assert convert(145_000.55, "money") == (145_000.55, [])
    assert convert("1500", "money") == (1500, [])
    assert convert(-3000.0, "money") == (-3000, [])


def test_text_is_passed_through():
    assert convert("Jointly", "text") == ("Jointly", [])


@pytest.mark.parametrize("value,kind", [("abc", "money"), ("n/a", "int"), (True, "money"), ("1952", "date"),
                                        (datetime(2026, 1, 1), "text")])
def test_unusable_values_become_null_and_are_reported(value, kind):
    result, problems = convert(value, kind)
    assert result is None and len(problems) == 1 and "inpX" in problems[0]
