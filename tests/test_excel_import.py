import json
from datetime import date, datetime
from decimal import Decimal
from io import BytesIO
from types import SimpleNamespace

import pytest

openpyxl = pytest.importorskip("openpyxl")
from openpyxl.workbook.defined_name import DefinedName  # noqa: E402

from app import excel_import, scenario_io  # noqa: E402

ROWS = [
    SimpleNamespace(Name="inpTaxYear", Cell="H10", Type="int"),
    SimpleNamespace(Name="inpFilingStatus", Cell="C3", Type="text"),
    SimpleNamespace(Name="inpDateOfBirth", Cell="C4", Type="date"),
    SimpleNamespace(Name="inpPriorYearEndIRABalance", Cell="C5", Type="money"),
    SimpleNamespace(Name="inpIRAConversion", Cell="C11", Type="money"),
    SimpleNamespace(Name="inpTaxWithheld", Cell="C42", Type="money"),
]


def make_workbook(extra=None) -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "TaxSheetSingle"
    ws["H10"], ws["C3"], ws["C4"], ws["C5"] = 2026, "Jointly", datetime(1952, 4, 14), 1_000_000
    ws["C11"], ws["Z1"], ws["C42"] = 999, 500, 16_500.5
    wb.defined_names["inpTaxYear"] = DefinedName("inpTaxYear", attr_text="TaxSheetSingle!$H$10")
    # a sheet-scoped name that points away from the fixed address: the name must win
    ws.defined_names["inpIRAConversion"] = DefinedName("inpIRAConversion", attr_text="TaxSheetSingle!$Z$1")
    meta = wb.create_sheet("version")
    meta["B4"] = "2026.3.0"
    if extra:
        extra(wb, ws, meta)
    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


def values(conversion):
    return {p["name"]: p["value"] for p in json.loads(conversion.json_text)["inputs"]}


def test_reads_names_scoped_names_and_addresses():
    conversion = excel_import.convert_workbook(make_workbook(), ROWS, "Maxwell_2026-Roth.xlsx")
    found = values(conversion)
    assert found == {"inpTaxYear": 2026, "inpFilingStatus": "Jointly", "inpDateOfBirth": "1952-04-14",
                     "inpPriorYearEndIRABalance": 1_000_000, "inpIRAConversion": 500, "inpTaxWithheld": 16_500.5}
    assert conversion.filled == 6 and conversion.blank == []


def test_title_comes_from_the_file_name_unless_the_workbook_has_one():
    assert excel_import.convert_workbook(make_workbook(), ROWS, "Maxwell_2026-Roth.xlsx").title == "Maxwell 2026 Roth"
    assert excel_import.convert_workbook(make_workbook(), ROWS, None).title == excel_import.DEFAULT_TITLE
    titled = make_workbook(lambda wb, ws, meta: meta.__setitem__("B12", "  Smith Plan "))
    assert excel_import.convert_workbook(titled, ROWS, "x.xlsx").title == "Smith Plan"


def test_blank_cells_are_null_and_counted():
    data = make_workbook(lambda wb, ws, meta: ws.__setitem__("C42", None))
    conversion = excel_import.convert_workbook(data, ROWS)
    assert values(conversion)["inpTaxWithheld"] is None and conversion.blank == ["inpTaxWithheld"]


def test_unusable_cells_become_warnings():
    data = make_workbook(lambda wb, ws, meta: ws.__setitem__("C5", "lots"))
    conversion = excel_import.convert_workbook(data, ROWS)
    assert values(conversion)["inpPriorYearEndIRABalance"] is None
    assert any("inpPriorYearEndIRABalance" in w for w in conversion.warnings)


def test_workbook_metadata_is_carried_over():
    stamp = datetime(2026, 11, 16, 10, 30)
    data = make_workbook(lambda wb, ws, meta: meta.__setitem__("B13", stamp))
    payload = json.loads(excel_import.convert_workbook(data, ROWS).json_text)
    assert payload["workbookVersion"] == "2026.3.0" and payload["lastUpdated"] == "2026-11-16T10:30:00"


def test_missing_input_sheet_and_bad_files_are_rejected():
    wb = openpyxl.Workbook()
    wb.active.title = "Other"
    buffer = BytesIO()
    wb.save(buffer)
    with pytest.raises(excel_import.WorkbookError, match="TaxSheetSingle"):
        excel_import.convert_workbook(buffer.getvalue(), ROWS)
    with pytest.raises(excel_import.WorkbookError, match="Excel"):
        excel_import.convert_workbook(b"not a workbook", ROWS)


def test_converted_json_loads_through_scenario_import(tables):
    rows = tables.rows("tblInputMap")
    conversion = excel_import.convert_workbook(make_workbook(), rows, "Maxwell_2026.xlsx")
    result = scenario_io.import_scenario(conversion.json_text, tables)
    assert result.report_title == "Maxwell 2026"
    assert result.values["tax_year"] == 2026
    assert result.values["dob"] == date(1952, 4, 14)
    assert result.values["prior_ye_ira_balance"] == Decimal(1_000_000)
    assert result.values["ira_conversion"] == Decimal(500)
