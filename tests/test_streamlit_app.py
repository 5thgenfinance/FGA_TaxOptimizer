from pathlib import Path

import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest  # noqa: E402

APP = str(Path(__file__).resolve().parent.parent / "streamlit_app.py")


def run_app() -> AppTest:
    return AppTest.from_file(APP, default_timeout=30).run()


def test_app_runs_without_exception():
    assert not run_app().exception


def test_entering_income_recalculates():
    at = run_app()
    at.number_input(key="in_wages_and_tips").set_value(145000.0).run()
    assert not at.exception
    assert at.session_state["in_wages_and_tips"] == 145000.0


def test_optional_checkbox_and_legacy_toggle():
    at = run_app()
    at.checkbox(key="has_spouse_dob").check().run()
    at.checkbox(key="legacy_mode").check().run()
    assert not at.exception
    assert at.session_state["has_spouse_dob"] is True
