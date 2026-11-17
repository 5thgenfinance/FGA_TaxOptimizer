"""Convert an uploaded Excel workbook (the TaxRetirementOptimizer template) to scenario JSON.

Pure Python (openpyxl), so it works on Streamlit Community Cloud with no Excel installed. The
JSON has the same shape as ``scenario_io.export_scenario`` writes, so it is validated and
loaded by ``scenario_io.import_scenario``.

Each input is located by, in order: its current name, its old names (excel/input_name_aliases.csv,
for workbooks from before the naming-convention migration) and finally its fixed cell address.
"""
from __future__ import annotations

import csv
import io
import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any, Iterable, Mapping

from app.excel_values import to_json_value

INPUT_SHEET = "TaxSheetSingle"
META_SHEET = "version"
VERSION_CELL = "B4"
TITLE_CELL = "B12"
UPDATED_CELL = "B13"
SCHEMA_VERSION = "1.0"
DEFAULT_TITLE = "Tax Retirement Optimizer Scenario"
MAX_BYTES = 25 * 1024 * 1024
ALIAS_FILE = Path(__file__).resolve().parents[1] / "excel" / "input_name_aliases.csv"


class WorkbookError(ValueError):
    """The uploaded file is not a usable Tax Retirement Optimizer workbook."""


@dataclass
class Conversion:
    json_text: str
    title: str
    filled: int
    blank: list[str]
    warnings: list[str] = field(default_factory=list)
    via_alias: dict[str, str] = field(default_factory=dict)
    via_address: list[str] = field(default_factory=list)


def load_aliases(path: Path | str = ALIAS_FILE) -> dict[str, list[str]]:
    """Old names per current input name, in priority order (file order). Missing file -> {}."""
    try:
        text = Path(path).read_text(encoding="utf-8-sig")
    except OSError:
        return {}
    aliases: dict[str, list[str]] = {}
    for row in csv.DictReader(io.StringIO(text)):
        name, alias = (row.get("Name") or "").strip(), (row.get("Alias") or "").strip()
        if name and alias and not name.startswith("#"):
            aliases.setdefault(name, []).append(alias)
    return aliases


def _single_cell(defined_name: Any, wb: Any):
    """The worksheet cell a defined name points at, or None if it is not a single cell."""
    try:
        destinations = list(defined_name.destinations)
    except Exception:  # #REF!, formulas and LAMBDAs have no cell destination
        return None
    if len(destinations) != 1:
        return None
    sheet, coord = destinations[0]
    coord = coord.replace("$", "")
    if sheet not in wb.sheetnames or ":" in coord:
        return None
    return wb[sheet][coord]


def _scopes(wb: Any, ws: Any) -> list[dict[str, Any]]:
    """Defined names by lower-case name (Excel names are case-insensitive): workbook, then sheet."""
    return [{key.lower(): value for key, value in scope.items()} for scope in (wb.defined_names, ws.defined_names)]


def _find(wb: Any, scopes: list[dict[str, Any]], name: str):
    for scope in scopes:
        defined = scope.get(name.lower())
        if defined is not None:
            cell = _single_cell(defined, wb)
            if cell is not None:
                return cell
    return None


def _input_cell(wb: Any, ws: Any, scopes: list[dict[str, Any]], row: Any, aliases: Mapping[str, list[str]]):
    """Find an input's cell. Order: current name, then old names (priority order), then address.

    Returns (cell, source) where source is "name", "alias:<old name>" or "address".
    """
    cell = _find(wb, scopes, row.Name)
    if cell is not None:
        return cell, "name"
    for alias in aliases.get(row.Name, []):
        cell = _find(wb, scopes, alias)
        if cell is not None:
            return cell, f"alias:{alias}"
    return ws[row.Cell], "address"


def _timestamp(value: Any) -> str:
    if isinstance(value, datetime):
        return value.replace(microsecond=0).isoformat()
    if isinstance(value, str):
        try:
            datetime.fromisoformat(value)
            return value
        except ValueError:
            pass
    return datetime.now().replace(microsecond=0).isoformat()


def _title(meta: Any, filename: str | None) -> str:
    stored = meta[TITLE_CELL].value if meta is not None else None
    if isinstance(stored, str) and stored.strip():
        return stored.strip()[:200]
    stem = re.sub(r"[_\-]+", " ", Path(filename or "").stem).strip()
    return stem[:200] or DEFAULT_TITLE


def convert_workbook(data: bytes, input_rows: Iterable[Any], filename: str | None = None,
                     aliases: Mapping[str, list[str]] | None = None) -> Conversion:
    """Read the input cells of ``data`` (an .xlsx/.xlsm file) and build scenario JSON.

    ``input_rows`` are the tblInputMap rows (Name, Cell, Type). Blank cells become null.
    ``aliases`` maps a current input name to its old names (default: excel/input_name_aliases.csv);
    current names always win, then old names, then the fixed cell address.
    """
    if aliases is None:
        aliases = load_aliases()
    if len(data) > MAX_BYTES:
        raise WorkbookError("The workbook is larger than 25 MB.")
    try:
        from openpyxl import load_workbook
        wb = load_workbook(BytesIO(data), data_only=True)
    except ImportError as exc:
        raise WorkbookError("Excel import needs the openpyxl package (pip install openpyxl).") from exc
    except Exception as exc:  # corrupt zip, wrong format, password protected
        raise WorkbookError("This does not look like an Excel .xlsx/.xlsm workbook "
                            f"({type(exc).__name__}).") from exc
    if INPUT_SHEET not in wb.sheetnames:
        raise WorkbookError(f"Worksheet '{INPUT_SHEET}' was not found. "
                            f"This file has: {', '.join(wb.sheetnames)}.")
    ws = wb[INPUT_SHEET]
    meta = wb[META_SHEET] if META_SHEET in wb.sheetnames else None

    scopes = _scopes(wb, ws)
    pairs, blank, problems, via_alias, via_address = [], [], [], {}, []
    for row in input_rows:
        cell, source = _input_cell(wb, ws, scopes, row, aliases)
        if source.startswith("alias:"):
            via_alias[row.Name] = source.split(":", 1)[1]
        elif source == "address" and row.Name in aliases:  # inputs that never had a name stay quiet
            via_address.append(getattr(row, "Label", row.Name))
        value = to_json_value(row.Name, cell.value, row.Type, problems)
        if value is None:
            blank.append(row.Name)
        pairs.append({"name": row.Name, "value": value})

    title = _title(meta, filename)
    version = ""
    if meta is not None and meta[VERSION_CELL].value is not None:
        version = str(meta[VERSION_CELL].value)
    payload = {
        "schemaVersion": SCHEMA_VERSION,
        "reportTitle": title,
        "lastUpdated": _timestamp(meta[UPDATED_CELL].value if meta is not None else None),
        "workbookVersion": version,
        "inputs": pairs,
    }
    warnings = [f"Workbook cell skipped: {p}" for p in problems]
    if via_alias:
        found = ", ".join(f"{old} -> {new}" for new, old in via_alias.items())
        warnings.append(f"This workbook uses old input names (found {len(via_alias)}): {found}.")
    if via_address:
        warnings.append("No named range found, so these were read by cell address: " + ", ".join(via_address) + ".")
    return Conversion(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", title,
                      len(pairs) - len(blank), blank, warnings, via_alias, via_address)
