"""Streamlit form state helpers (pure functions over a dict-like session state).

Each input in tblInputMap.csv has a widget key ``in_<field>``. Optional inputs
(spouse DOB, Schedule A SALT) also have a checkbox key ``has_<field>``.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, MutableMapping

from app.models import FilerInputs
from app.scenario_io import DEFAULT_TITLE
from app.tables import Tables

OPTIONAL_FIELDS = frozenset({"spouse_dob", "schedule_a_salt"})
STATUS_OPTIONS = ("Single", "Jointly")
DEFAULT_DOB = date(1960, 1, 1)


def state_key(field: str) -> str:
    return f"in_{field}"


def flag_key(field: str) -> str:
    return f"has_{field}"


def default_tax_year(tables: Tables, today: date | None = None) -> int:
    """The current calendar year if supported, otherwise the latest supported year."""
    years = tables.supported_years()
    current = (today or date.today()).year
    return current if current in years else years[-1]


def default_value(row, tables: Tables) -> Any:
    if row.Field == "tax_year":
        return default_tax_year(tables)
    if row.Field == "filing_status":
        return STATUS_OPTIONS[0]
    if row.Type == "date":
        return DEFAULT_DOB
    if row.Type == "money":
        return 0.0
    if row.Type == "int":
        return 0
    return ""


def groups(tables: Tables) -> list[tuple[str, list]]:
    """Input rows grouped by tblInputMap Group, in order of first appearance."""
    result: dict[str, list] = {}
    for row in tables.rows("tblInputMap"):
        result.setdefault(row.Group, []).append(row)
    return list(result.items())


def init_state(state: MutableMapping, tables: Tables) -> None:
    for row in tables.rows("tblInputMap"):
        state.setdefault(state_key(row.Field), default_value(row, tables))
        if row.Field in OPTIONAL_FIELDS:
            state.setdefault(flag_key(row.Field), False)
    state.setdefault("report_title", DEFAULT_TITLE)
    state.setdefault("last_updated", datetime.now().replace(microsecond=0).isoformat())


def read_state(state: MutableMapping, tables: Tables) -> FilerInputs:
    """Build FilerInputs from widget state."""
    kwargs: dict[str, Any] = {}
    for row in tables.rows("tblInputMap"):
        value = state[state_key(row.Field)]
        if row.Field in OPTIONAL_FIELDS and not state[flag_key(row.Field)]:
            kwargs[row.Field] = None
        elif row.Type == "money":
            kwargs[row.Field] = Decimal(str(value))
        else:
            kwargs[row.Field] = value
    return FilerInputs(**kwargs)


def apply_import(state: MutableMapping, values: dict[str, Any], tables: Tables) -> list[str]:
    """Write imported values into widget state; returns warnings for skipped values."""
    warnings: list[str] = []
    for row in tables.rows("tblInputMap"):
        if row.Field not in values:
            continue  # field absent from the file: leave the current value unchanged
        value = values[row.Field]
        if row.Field == "filing_status" and value is not None and value not in STATUS_OPTIONS:
            warnings.append(f"Filing status {value!r} is not available in the form; ignored")
            continue
        if row.Field in OPTIONAL_FIELDS:
            state[flag_key(row.Field)] = value is not None
        if value is None:
            state[state_key(row.Field)] = default_value(row, tables)
        elif row.Type == "money":
            state[state_key(row.Field)] = float(value)
        else:
            state[state_key(row.Field)] = value
    return warnings
