from decimal import Decimal

from app.display import display_records, format_limit
from app.tables import load_all


def test_format_limit():
    assert format_limit(Decimal("9999999")) == "No limit"
    assert format_limit(Decimal("640600")) == "640,600"


def test_bracket_sentinels_shown_as_no_limit():
    recs = display_records("tblTaxRate", load_all().rows("tblTaxRate"))
    top_2025 = [r for r in recs if r["Year"] == 2025 and r["Bucket"] == 7][0]
    assert top_2025["Single"] == "No limit"
    first = recs[0]
    assert first["Single"] == "12,400" and first["Rate"] == 0.1


def test_other_tables_use_floats():
    recs = display_records("tblAMT", load_all().rows("tblAMT"))
    assert recs[0]["Exemption"] == 90100.0
