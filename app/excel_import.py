"""Convert an uploaded Excel workbook (the TaxRetirementOptimizer template) to scenario JSON.

Pure Python (openpyxl), so it works on Streamlit Community Cloud with no Excel installed. The
JSON has the same shape as ``scenario_io.export_scenario`` writes, so it is validated and
loaded by ``scenario_io.import_scenario``.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any, Iterable

from app.excel_values import to_json_value

INPUT_SHEET = "TaxSheetSingle"
META_SHEET = "version"
VERSION_CELL = "B4"
TITLE_CELL = "B12"
UPDATED_CELL = "B13"
SCHEMA_VERSION = "1.0"
DEFAULT_TITLE = "Tax Retirement Optimizer Scenario"
MAX_BYTES = 25 * 1024 * 1024


class WorkbookError(ValueError):
    """The uploaded file is not a usable Tax Retirement Optimizer workbook."""


@dataclass
class Conversion:
    json_text: str
    title: str
    filled: int
    blank: list[str]
    warnings: list[str] = field(default_factory=list)


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


def _input_cell(wb: Any, ws: Any, name: str, address: str):
    """Prefer the workbook-wide name, then the sheet-scoped name, then the fixed address."""
    for scope in (wb.defined_names, ws.defined_names):
        defined = scope.get(name)
        if defined is not None:
            cell = _single_cell(defined, wb)
            if cell is not None:
                return cell
    return ws[address]


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


def convert_workbook(data: bytes, input_rows: Iterable[Any], filename: str | None = None) -> Conversion:
    """Read the input cells of ``data`` (an .xlsx/.xlsm file) and build scenario JSON.

    ``input_rows`` are the tblInputMap rows (Name, Cell, Type). Blank cells become null.
    """
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

    pairs, blank, problems = [], [], []
    for row in input_rows:
        cell = _input_cell(wb, ws, row.Name, row.Cell)
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
    return Conversion(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", title,
                      len(pairs) - len(blank), blank, warnings)
