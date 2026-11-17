from pathlib import Path

import pytest

from app import input_help

APP = str(Path(__file__).resolve().parent.parent / "streamlit_app.py")


def test_every_input_has_a_tooltip(tables):
    missing = [row.Field for row in tables.rows("tblInputMap") if not input_help.help_for(row.Field)]
    assert missing == [], f"add tooltip text to app/input_help.py for: {missing}"


def test_no_tooltip_for_an_unknown_field(tables):
    fields = {row.Field for row in tables.rows("tblInputMap")}
    assert set(input_help.HELP) <= fields


def test_tooltips_are_short_complete_sentences():
    for field, text in input_help.HELP.items():
        assert text == text.strip() and text.endswith("."), field
        assert 30 <= len(text) <= 300, (field, len(text))


def test_every_widget_in_the_app_shows_its_tooltip(tables):
    pytest.importorskip("streamlit")
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(APP, default_timeout=30).run()
    assert not at.exception
    for row in tables.rows("tblInputMap"):
        key = f"in_{row.Field}"
        if row.Field in ("tax_year", "filing_status"):
            widget = at.selectbox(key=key)
        elif row.Type == "date":
            widget = at.date_input(key=key)
        elif row.Type == "money":
            widget = at.number_input(key=key)
        else:
            widget = at.text_input(key=key)
        assert widget.help == input_help.help_for(row.Field), row.Field
        if row.Field in ("spouse_dob", "schedule_a_salt"):
            assert at.checkbox(key=f"has_{row.Field}").help == input_help.help_for(row.Field), row.Field
