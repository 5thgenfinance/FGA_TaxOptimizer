from pathlib import Path

import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest  # noqa: E402

APP = str(Path(__file__).resolve().parent.parent / "streamlit_app.py")


def run_app() -> AppTest:
    return AppTest.from_file(APP, default_timeout=60).run()


def test_the_curves_are_on_by_default_and_the_app_runs():
    at = run_app()
    assert not at.exception
    assert at.checkbox(key="wi_curves").value is True


def test_the_curves_can_be_turned_off_and_on():
    at = run_app()
    at.checkbox(key="wi_curves").uncheck().run()
    assert not at.exception
    at.checkbox(key="wi_curves").check().run()
    assert not at.exception


def test_the_marginal_rate_target_can_be_changed():
    at = run_app()
    assert at.selectbox(key="wi_ira_cap").value == 22
    at.selectbox(key="wi_ira_cap").set_value(12).run()
    assert not at.exception
    assert at.session_state["wi_ira_cap"] == 12


def test_curves_follow_the_other_sliders_without_errors():
    at = run_app()
    at.slider(key="wi_ira").set_value(40_000).run()
    at.slider(key="wi_ltcg").set_value(60_000).run()
    at.slider(key="wi_deductions").set_value(30_000).run()
    assert not at.exception
