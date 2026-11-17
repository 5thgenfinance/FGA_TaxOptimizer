import json
from datetime import date, datetime
from decimal import Decimal

import pytest

from app import scenario_io as sio
from app.models import FilerInputs

NOW = datetime(2026, 11, 16, 18, 53, 7, 999)


@pytest.fixture()
def golden():
    return FilerInputs(
        tax_year=2026, filing_status="Jointly", dob=date(1952, 4, 14), spouse_dob=date(1974, 9, 30),
        prior_ye_ira_balance=1_000_000, qualified_dividends=1_800, taxable_interest=900,
        ordinary_dividends=2_400, short_term_gain_loss=-3_000, wages_and_tips=145_000,
        long_term_capital_gains=6_000, schedule_a_deductions=12_000, tax_withheld=16_500,
    )


def minimal(**overrides):
    doc = {"schemaVersion": "1.0", "reportTitle": "T", "lastUpdated": "2026-11-16T18:53:00", "inputs": []}
    doc.update(overrides)
    return json.dumps(doc)


def test_export_structure_and_order(golden, tables):
    doc = json.loads(sio.export_scenario(golden, "  My study ", tables, "2026.3.0", NOW))
    assert list(doc) == ["schemaVersion", "reportTitle", "lastUpdated", "workbookVersion", "inputs"]
    assert doc["reportTitle"] == "My study"
    assert doc["lastUpdated"] == "2026-11-16T18:53:07"
    assert [p["name"] for p in doc["inputs"]] == [r.Name for r in tables.rows("tblInputMap")]
    values = {p["name"]: p["value"] for p in doc["inputs"]}
    assert values["inpTaxYear"] == 2026 and values["inpFilingStatus"] == "Jointly"
    assert values["inpDateOfBirth"] == "1952-04-14"
    assert values["inpPriorYearEndIRABalance"] == 1_000_000
    assert values["inpScheduleASALT"] is None
    assert values["inpShortTermCapitalGainLoss"] == -3_000


def test_round_trip(golden, tables):
    result = sio.import_scenario(sio.export_scenario(golden, "Round trip", tables, now=NOW), tables)
    assert result.report_title == "Round trip" and result.last_updated == "2026-11-16T18:53:07"
    assert result.warnings == []
    assert FilerInputs(**result.values) == golden


def test_fractional_money_round_trips(golden, tables):
    golden.wages_and_tips = Decimal("145000.55")
    result = sio.import_scenario(sio.export_scenario(golden, "x", tables), tables)
    assert result.values["wages_and_tips"] == Decimal("145000.55")


def test_bom_prefixed_file(golden, tables):
    text = "\ufeff" + sio.export_scenario(golden, "x", tables)
    assert sio.import_scenario(text, tables).values["tax_year"] == 2026


def test_missing_names_leave_values_absent(tables):
    result = sio.import_scenario(minimal(inputs=[{"name": "inpTaxYear", "value": 2026}]), tables)
    assert result.values == {"tax_year": 2026}


def test_unknown_name_and_bad_year_and_status_warn(tables):
    text = minimal(inputs=[
        {"name": "inpBogus", "value": 1},
        {"name": "inpTaxYear", "value": 2031},
        {"name": "inpFilingStatus", "value": "head of household"},
        {"name": "inpWagesAndTips", "value": 5},
    ])
    result = sio.import_scenario(text, tables)
    assert result.values == {"wages_and_tips": Decimal(5)}
    assert len(result.warnings) == 3


def test_status_alias_normalized(tables):
    result = sio.import_scenario(minimal(inputs=[{"name": "inpFilingStatus", "value": "MFJ"}]), tables)
    assert result.values["filing_status"] == "Jointly"


def test_null_values_allowed(tables):
    result = sio.import_scenario(minimal(inputs=[{"name": "inpSpouseDateOfBirth", "value": None}]), tables)
    assert result.values == {"spouse_dob": None}


@pytest.mark.parametrize("text,fragment", [
    ("not json", "Not valid JSON"),
    ("[]", "root must be an object"),
    (json.dumps({"schemaVersion": "1.0", "lastUpdated": "2026-11-16T10:00:00", "inputs": []}), "reportTitle"),
    (minimal(reportTitle="   "), "reportTitle"),
    (minimal(reportTitle="x" * 201), "reportTitle"),
    (minimal(lastUpdated="yesterday"), "lastUpdated"),
    (minimal(schemaVersion="2.0"), "schemaVersion"),
    (minimal(inputs=[{"name": "inpDateOfBirth", "value": "04/14/1952"}]), "inpDateOfBirth"),
    (minimal(inputs=[{"name": "inpWagesAndTips", "value": "145000"}]), "inpWagesAndTips"),
    (minimal(inputs=[{"name": "inpWagesAndTips", "value": True}]), "inpWagesAndTips"),
    (minimal(inputs=[{"name": "inpTaxYear", "value": 2026.5}]), "inpTaxYear"),
    (minimal(inputs=[{"name": "inpFilingStatus", "value": 5}]), "inpFilingStatus"),
])
def test_invalid_files_rejected(tables, text, fragment):
    with pytest.raises(sio.ScenarioError) as exc:
        sio.import_scenario(text, tables)
    assert fragment in str(exc.value)


def test_all_errors_reported_together(tables):
    text = minimal(inputs=[{"name": "inpWagesAndTips", "value": "x"}, {"name": "inpDateOfBirth", "value": "bad"}])
    with pytest.raises(sio.ScenarioError) as exc:
        sio.import_scenario(text, tables)
    assert len(exc.value.errors) == 2


def test_export_requires_title(golden, tables):
    with pytest.raises(sio.ScenarioError):
        sio.export_scenario(golden, "   ", tables)


def test_safe_filename():
    assert sio.safe_filename("Maxwell 2026: Roth/Conversion!") == "Maxwell_2026_Roth_Conversion.json"
    assert sio.safe_filename("???") == "scenario.json"
