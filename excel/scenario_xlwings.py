"""Excel <-> scenario JSON using xlwings.

Usage (workbook open in Excel):
    python excel/scenario_xlwings.py export --file scenario.json --title "My report"
    python excel/scenario_xlwings.py import --file scenario.json

The input list, order and cell fallbacks come from data/tblInputMap.csv.
"""
from __future__ import annotations

import argparse
import csv
import json
from datetime import date, datetime
from pathlib import Path

import xlwings as xw

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
INPUT_SHEET = "TaxSheetSingle"
META_SHEET = "version"
VERSION_CELL = "B4"
TITLE_NAME, TITLE_CELL = "inpReportTitle", "B12"
UPDATED_NAME, UPDATED_CELL = "inpLastUpdated", "B13"
SCHEMA_VERSION = "1.0"
DEFAULT_TITLE = "Tax Retirement Optimizer Scenario"


def load_input_map(path: Path = DATA_DIR / "tblInputMap.csv") -> list[dict]:
    with open(path, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    return sorted(rows, key=lambda r: int(r["Order"]))


def _resolve(sheet, name: str, addr: str):
    """Return the range for a named input, falling back to its cell address."""
    for ref in (name, addr):
        try:
            rng = sheet.range(ref)
            _ = rng.address
            return rng
        except Exception:
            continue
    return None


def _is_formula(rng) -> bool:
    f = rng.formula
    return isinstance(f, str) and f.startswith("=")


def _to_json_value(v, typ: str):
    if v is None or v == "":
        return None
    if isinstance(v, datetime):
        return v.date().isoformat()
    if isinstance(v, date):
        return v.isoformat()
    if typ == "int":
        return int(v)
    if typ == "money" and isinstance(v, (int, float)):
        return int(v) if float(v).is_integer() else float(v)
    return v


def _from_json_value(v, typ: str):
    if v is None:
        return None
    if typ == "date":
        return datetime.strptime(str(v), "%Y-%m-%d")
    if typ == "int":
        return int(v)
    if typ == "money":
        return float(v)
    return v


def _meta(book, name: str, addr: str):
    return _resolve(book.sheets[META_SHEET], name, addr)


def export_scenario(book, path, title: str | None = None) -> dict:
    ws = book.sheets[INPUT_SHEET]
    title_rng = _meta(book, TITLE_NAME, TITLE_CELL)
    updated_rng = _meta(book, UPDATED_NAME, UPDATED_CELL)
    if title:
        title_rng.value = title
    report_title = (title_rng.value if title_rng is not None else None) or title or DEFAULT_TITLE
    stamp = datetime.now().replace(microsecond=0).isoformat()
    if updated_rng is not None:
        updated_rng.value = stamp

    version_rng = book.sheets[META_SHEET].range(VERSION_CELL)
    inputs, missing = [], []
    for row in load_input_map():
        rng = _resolve(ws, row["Name"], row["Cell"])
        if rng is None:
            missing.append(row["Name"])
            value = None
        elif _is_formula(rng):
            value = None
        else:
            value = _to_json_value(rng.value, row["Type"])
        inputs.append({"name": row["Name"], "value": value})

    payload = {
        "schemaVersion": SCHEMA_VERSION,
        "reportTitle": str(report_title),
        "lastUpdated": stamp,
        "workbookVersion": str(version_rng.value or ""),
        "inputs": inputs,
    }
    Path(path).write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {"exported": len(inputs), "cells_not_found": missing}


def import_scenario(book, path) -> dict:
    data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if str(data.get("schemaVersion", "")).split(".")[0] != SCHEMA_VERSION.split(".")[0]:
        raise ValueError(f"Unsupported schemaVersion: {data.get('schemaVersion')!r}")
    if not data.get("reportTitle"):
        raise ValueError("reportTitle is required")

    ws = book.sheets[INPUT_SHEET]
    by_name = {r["Name"]: r for r in load_input_map()}
    applied, skipped, unknown = 0, [], []

    for item in data.get("inputs", []):
        name = item.get("name")
        row = by_name.get(name)
        if row is None:
            unknown.append(name)
            continue
        rng = _resolve(ws, name, row["Cell"])
        if rng is None:
            skipped.append(f"{name} (cell not found)")
            continue
        if _is_formula(rng):
            skipped.append(f"{name} (formula cell)")
            continue
        value = _from_json_value(item.get("value"), row["Type"])
        if value is None:
            rng.clear_contents()
        else:
            rng.value = value
        applied += 1

    title_rng = _meta(book, TITLE_NAME, TITLE_CELL)
    updated_rng = _meta(book, UPDATED_NAME, UPDATED_CELL)
    if title_rng is not None:
        title_rng.value = data["reportTitle"]
    if updated_rng is not None and data.get("lastUpdated"):
        updated_rng.value = data["lastUpdated"]

    book.app.calculate()
    return {"applied": applied, "skipped": skipped, "unknown_names": unknown}


def _open_book(book_path: str | None):
    return xw.Book(book_path) if book_path else xw.books.active


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    for cmd in ("export", "import"):
        p = sub.add_parser(cmd)
        p.add_argument("--file", required=True, help="scenario JSON path")
        p.add_argument("--book", help="workbook path (default: active workbook)")
        if cmd == "export":
            p.add_argument("--title", help="report title to store and export")
    args = parser.parse_args()

    book = _open_book(args.book)
    if args.cmd == "export":
        result = export_scenario(book, args.file, args.title)
    else:
        result = import_scenario(book, args.file)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
