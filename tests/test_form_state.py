from datetime import date
from decimal import Decimal

from app import form_state as fs


def make_state(tables):
    state = {}
    fs.init_state(state, tables)
    return state


def test_default_tax_year_prefers_current_year(tables):
    assert fs.default_tax_year(tables, today=date(2026, 11, 16)) == 2026
    assert fs.default_tax_year(tables, today=date(2027, 3, 1)) == 2027
    assert fs.default_tax_year(tables, today=date(2020, 1, 1)) == 2027  # not supported: latest year
    assert fs.default_tax_year(tables, today=date(2031, 1, 1)) == 2027


def test_defaults_build_valid_inputs(tables):
    state = make_state(tables)
    inputs = fs.read_state(state, tables)
    assert inputs.tax_year == fs.default_tax_year(tables) and inputs.filing_status == "Single"
    assert inputs.dob == date(1960, 1, 1)
    assert inputs.spouse_dob is None and inputs.schedule_a_salt is None
    assert inputs.wages_and_tips == Decimal(0)
    assert state["report_title"] and state["last_updated"]


def test_init_does_not_overwrite_existing(tables):
    state = {"in_wages_and_tips": 5.0}
    fs.init_state(state, tables)
    assert state["in_wages_and_tips"] == 5.0


def test_optional_fields_follow_checkbox(tables):
    state = make_state(tables)
    state["in_spouse_dob"] = date(1970, 1, 2)
    assert fs.read_state(state, tables).spouse_dob is None
    state["has_spouse_dob"] = True
    assert fs.read_state(state, tables).spouse_dob == date(1970, 1, 2)
    state["has_schedule_a_salt"] = True
    state["in_schedule_a_salt"] = 0.0
    assert fs.read_state(state, tables).schedule_a_salt == Decimal(0)


def test_apply_import_round_trip(tables):
    values = {"tax_year": 2026, "filing_status": "Jointly", "dob": date(1952, 4, 14),
              "spouse_dob": date(1974, 9, 30), "wages_and_tips": Decimal("145000.5"),
              "schedule_a_salt": None}
    state = make_state(tables)
    assert fs.apply_import(state, values, tables) == []
    inputs = fs.read_state(state, tables)
    assert inputs.filing_status == "Jointly" and inputs.spouse_dob == date(1974, 9, 30)
    assert inputs.wages_and_tips == Decimal("145000.5") and inputs.schedule_a_salt is None


def test_absent_fields_unchanged_and_null_resets_to_default(tables):
    state = make_state(tables)
    state["in_wages_and_tips"] = 99.0
    state["in_taxable_interest"] = 50.0
    fs.apply_import(state, {"taxable_interest": None}, tables)
    assert state["in_wages_and_tips"] == 99.0
    assert state["in_taxable_interest"] == 0.0


def test_unavailable_status_is_skipped_with_warning(tables):
    state = make_state(tables)
    warnings = fs.apply_import(state, {"filing_status": "Separate"}, tables)
    assert state["in_filing_status"] == "Single" and len(warnings) == 1


def test_groups_keep_input_map_order(tables):
    names = [g for g, _ in fs.groups(tables)]
    assert names == ["Filer", "Retirement", "Investments", "Other income", "Deductions", "AMT", "Payments"]
    assert sum(len(rows) for _, rows in fs.groups(tables)) == 21
