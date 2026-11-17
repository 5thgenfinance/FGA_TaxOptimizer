"""Convert cell values read through xlwings into scenario JSON values (no xlwings import)."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any

EXCEL_EPOCH = date(1899, 12, 30)


def _as_date(value: Any) -> date | None:
    """A date from a date, datetime, pywin32 datetime or Excel serial number; else None."""
    if hasattr(value, "isoformat"):
        day = value.date() if callable(getattr(value, "date", None)) else value
        return date(day.year, day.month, day.day)
    if isinstance(value, (int, float)) and not isinstance(value, bool) and 1 <= value < 2_958_466:
        return EXCEL_EPOCH + timedelta(days=int(value))
    return None


def to_json_value(name: str, value: Any, kind: str, problems: list[str]) -> Any:
    """JSON-safe value for one input cell; unusable values become None and are listed in ``problems``."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    if kind == "date":
        day = _as_date(value)
        if day is None:
            problems.append(f"{name}: expected a date, found {type(value).__name__} {value!r}")
            return None
        return day.isoformat()
    if kind in ("int", "money"):
        if isinstance(value, bool):
            problems.append(f"{name}: expected a number, found a Yes/No value")
            return None
        try:
            number = float(value)
        except (TypeError, ValueError):
            problems.append(f"{name}: expected a number, found {type(value).__name__} {value!r}")
            return None
        if kind == "int":
            return int(number)
        return int(number) if number.is_integer() else number
    if hasattr(value, "isoformat"):
        problems.append(f"{name}: expected text, found a date")
        return None
    return str(value)
