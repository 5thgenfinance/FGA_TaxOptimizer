"""Scenario JSON import/export (spec section 12).

The file holds a report title, a last-updated timestamp and the ordered
name/value pairs of the editable ``inp...`` inputs defined in tblInputMap.csv.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from app.calc.common import UnknownStatusError
from app.models import FilerInputs
from app.status import normalize_status
from app.tables import Tables

SCHEMA_VERSION = "1.0"
DEFAULT_TITLE = "Tax Retirement Optimizer Scenario"


class ScenarioError(ValueError):
    """The scenario file or request is invalid; ``errors`` lists every problem."""

    def __init__(self, errors: list[str]):
        self.errors = list(errors)
        super().__init__("; ".join(self.errors))


class InputPair(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    value: Any = None


class ScenarioFile(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    schema_version: str = Field(alias="schemaVersion")
    report_title: str = Field(alias="reportTitle", min_length=1, max_length=200)
    last_updated: str = Field(alias="lastUpdated")
    workbook_version: str = Field(default="", alias="workbookVersion")
    inputs: list[InputPair]

    @field_validator("report_title")
    @classmethod
    def _title_not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value

    @field_validator("last_updated")
    @classmethod
    def _iso_timestamp(cls, value: str) -> str:
        try:
            datetime.fromisoformat(value)
        except ValueError as exc:
            raise ValueError("must be an ISO 8601 timestamp") from exc
        return value


@dataclass
class ImportResult:
    report_title: str
    last_updated: str
    workbook_version: str
    values: dict[str, Any]
    warnings: list[str] = field(default_factory=list)


def timestamp(now: datetime | None = None) -> str:
    return (now or datetime.now()).replace(microsecond=0).isoformat()


def safe_filename(title: str) -> str:
    stem = re.sub(r"[^A-Za-z0-9._-]+", "_", title).strip("_")[:80]
    return f"{stem or 'scenario'}.json"


def _to_json_value(value: Any, kind: str) -> Any:
    if value is None:
        return None
    if kind == "date":
        return value.isoformat()
    if kind == "money":
        d = Decimal(value)
        return int(d) if d == d.to_integral_value() else float(d)
    if kind == "int":
        return int(value)
    return str(value)


def _from_json_value(name: str, value: Any, kind: str, errors: list[str]) -> Any:
    if value is None:
        return None
    if kind == "date":
        if not isinstance(value, str):
            errors.append(f"{name}: expected a YYYY-MM-DD string")
            return None
        try:
            return date.fromisoformat(value)
        except ValueError:
            errors.append(f"{name}: invalid date {value!r}")
            return None
    if kind in ("money", "int"):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            errors.append(f"{name}: expected a number")
            return None
        if kind == "int":
            if float(value) != int(value):
                errors.append(f"{name}: expected a whole number")
                return None
            return int(value)
        return Decimal(str(value))
    if not isinstance(value, str):
        errors.append(f"{name}: expected text")
        return None
    return value


def export_scenario(inputs: FilerInputs, title: str, tables: Tables,
                    workbook_version: str = "", now: datetime | None = None) -> str:
    """Serialize inputs to scenario JSON, in tblInputMap order."""
    title = (title or "").strip()
    if not title or len(title) > 200:
        raise ScenarioError(["Report title must be 1-200 characters"])
    pairs = [
        {"name": row.Name, "value": _to_json_value(getattr(inputs, row.Field), row.Type)}
        for row in tables.rows("tblInputMap")
    ]
    payload = {
        "schemaVersion": SCHEMA_VERSION,
        "reportTitle": title,
        "lastUpdated": timestamp(now),
        "workbookVersion": workbook_version,
        "inputs": pairs,
    }
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"


def import_scenario(text: str, tables: Tables) -> ImportResult:
    """Parse and validate scenario JSON.

    Returns the values present in the file keyed by FilerInputs field. Unknown
    names, unsupported tax years and unrecognized filing statuses become warnings.
    """
    try:
        raw = json.loads(text.lstrip("\ufeff"))
    except json.JSONDecodeError as exc:
        raise ScenarioError([f"Not valid JSON: {exc}"]) from exc
    if not isinstance(raw, dict):
        raise ScenarioError(["The JSON root must be an object"])
    try:
        scenario = ScenarioFile.model_validate(raw)
    except ValidationError as exc:
        raise ScenarioError([
            f"{'.'.join(str(p) for p in err['loc'])}: {err['msg']}" for err in exc.errors()
        ]) from exc
    if scenario.schema_version.split(".")[0] != SCHEMA_VERSION.split(".")[0]:
        raise ScenarioError([f"Unsupported schemaVersion {scenario.schema_version!r}"])

    by_name = {row.Name: row for row in tables.rows("tblInputMap")}
    errors: list[str] = []
    warnings: list[str] = []
    values: dict[str, Any] = {}
    for pair in scenario.inputs:
        row = by_name.get(pair.name)
        if row is None:
            warnings.append(f"Unknown input ignored: {pair.name}")
            continue
        value = _from_json_value(pair.name, pair.value, row.Type, errors)
        if value is not None and row.Field == "tax_year" and value not in tables.supported_years():
            warnings.append(f"Tax year {value} is not supported; ignored")
            continue
        if value is not None and row.Field == "filing_status":
            try:
                value = normalize_status(value, tables)
            except UnknownStatusError:
                warnings.append(f"Unrecognized filing status {value!r}; ignored")
                continue
        values[row.Field] = value
    if errors:
        raise ScenarioError(errors)
    return ImportResult(scenario.report_title, scenario.last_updated,
                        scenario.workbook_version, values, warnings)
