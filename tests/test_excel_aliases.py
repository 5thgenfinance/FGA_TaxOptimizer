import csv
import json
from datetime import datetime
from io import BytesIO
from types import SimpleNamespace

import pytest

openpyxl = pytest.importorskip("openpyxl")
from openpyxl.workbook.defined_name import DefinedName  # noqa: E402

from app import excel_import  # noqa: E402

ROWS = [
    SimpleNamespace(Name="inpDateOfBirth", Cell="C4", Type="date", Label="Date of birth"),
    SimpleNamespace(Name="inpIRAConversion", Cell="C11", Type="money", Label="IRA (Roth) conversion"),
    SimpleNamespace(Name="inpQualifiedDividends", Cell="C12", Type="money", Label="Qualified dividends"),
    SimpleNamespace(Name="inpTaxWithheld", Cell="C42", Type="money", Label="Tax withheld"),
]
ALIASES = {"inpDateOfBirth": ["DOB", "BirthDate"], "inpIRAConversion": ["RothConv"],
           "inpQualifiedDividends": ["QualDivs"]}


def build(names=(), scoped=()):
    """Workbook whose fixed cells hold decoys (111) and whose named cells (Z1..) hold the real values."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "TaxSheetSingle"
    ws["C4"], ws["C11"], ws["C12"], ws["C42"] = datetime(1900, 1, 1), 111, 111, 16_500
    ws["Z1"], ws["Z2"], ws["Z3"], ws["Z4"] = datetime(1952, 4, 14), 500, 700, 900
    for name, cell in names:
        wb.defined_names[name] = DefinedName(name, attr_text=f"TaxSheetSingle!${cell[0]}${cell[1:]}")
    for name, cell in scoped:
        ws.defined_names[name] = DefinedName(name, attr_text=f"TaxSheetSingle!${cell[0]}${cell[1:]}")
    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


def read(data, aliases=ALIASES):
    conversion = excel_import.convert_workbook(data, ROWS, "x.xlsx", aliases)
    return conversion, {p["name"]: p["value"] for p in json.loads(conversion.json_text)["inputs"]}


def test_old_names_are_used_when_the_new_names_are_missing():
    conversion, found = read(build(names=[("DOB", "Z1"), ("QualDivs", "Z3")], scoped=[("RothConv", "Z2")]))
    assert found["inpDateOfBirth"] == "1952-04-14"
    assert found["inpIRAConversion"] == 500 and found["inpQualifiedDividends"] == 700
    assert conversion.via_alias == {"inpDateOfBirth": "DOB", "inpIRAConversion": "RothConv",
                                    "inpQualifiedDividends": "QualDivs"}


def test_new_names_win_over_old_names():
    data = build(names=[("inpQualifiedDividends", "Z3"), ("QualDivs", "Z4")])
    conversion, found = read(data)
    assert found["inpQualifiedDividends"] == 700
    assert "inpQualifiedDividends" not in conversion.via_alias


def test_old_names_are_tried_in_file_order():
    _, found = read(build(names=[("BirthDate", "Z2"), ("DOB", "Z1")]))
    assert found["inpDateOfBirth"] == "1952-04-14"


def test_name_lookup_ignores_case():
    conversion, found = read(build(names=[("INPQUALIFIEDDIVIDENDS", "Z3"), ("dob", "Z1")]))
    assert found["inpQualifiedDividends"] == 700 and found["inpDateOfBirth"] == "1952-04-14"
    assert conversion.via_alias == {"inpDateOfBirth": "DOB"}


def test_warnings_explain_old_names_and_address_fallbacks():
    conversion, found = read(build(names=[("DOB", "Z1")]))
    assert found["inpTaxWithheld"] == 16_500  # no alias entry, so read by address without a warning
    assert any("old input names" in w and "DOB -> inpDateOfBirth" in w for w in conversion.warnings)
    note = next(w for w in conversion.warnings if "cell address" in w)
    assert "IRA (Roth) conversion" in note and "Qualified dividends" in note
    assert "Tax withheld" not in note and conversion.via_address == ["IRA (Roth) conversion", "Qualified dividends"]


def test_current_workbook_gives_no_old_name_warnings():
    data = build(names=[("inpDateOfBirth", "Z1"), ("inpQualifiedDividends", "Z3")], scoped=[("inpIRAConversion", "Z2")])
    conversion, _ = read(data)
    assert conversion.warnings == [] and conversion.via_alias == {}


def test_load_aliases_reads_priority_order_and_tolerates_a_missing_file(tmp_path):
    path = tmp_path / "a.csv"
    path.write_text("Name,Alias,Note\ninpA,old1,x\ninpA,old2,\n#inpB,skip,\ninpC,,empty\n", encoding="utf-8")
    assert excel_import.load_aliases(path) == {"inpA": ["old1", "old2"]}
    assert excel_import.load_aliases(tmp_path / "missing.csv") == {}


def test_shipped_alias_file_is_consistent_with_the_input_map(tables):
    aliases = excel_import.load_aliases()
    assert aliases, "excel/input_name_aliases.csv is missing or empty"
    current = {row.Name for row in tables.rows("tblInputMap")}
    assert set(aliases) <= current
    flat = [alias.lower() for olds in aliases.values() for alias in olds]
    assert len(flat) == len(set(flat)), "an old name maps to two inputs"
    assert not set(flat) & {name.lower() for name in current}, "an old name equals a current name"
    assert aliases["inpDateOfBirth"] == ["DOB"] and aliases["inpTaxYear"] == ["year"]
    with open(excel_import.ALIAS_FILE, newline="", encoding="utf-8-sig") as handle:
        assert next(csv.reader(handle)) == ["Name", "Alias", "Note"]
