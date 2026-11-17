from pathlib import Path

import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest  # noqa: E402

from app import curves  # noqa: E402

APP = str(Path(__file__).resolve().parent.parent / "streamlit_app.py")
SHOW = {lever: f"wi_show_{lever}" for lever in curves.LEVERS}


def run_app() -> AppTest:
    return AppTest.from_file(APP, default_timeout=60).run()


def test_every_lever_shows_its_curve_and_notes_by_default():
    at = run_app()
    assert not at.exception
    assert all(at.checkbox(key=key).value is True for key in SHOW.values())


def test_each_lever_can_be_hidden_and_shown_on_its_own():
    at = run_app()
    for lever, key in SHOW.items():
        at.checkbox(key=key).uncheck().run()
        assert not at.exception, lever
        assert at.checkbox(key=key).value is False
        others = [k for other, k in SHOW.items() if other != lever]
        assert all(at.checkbox(key=k).value is True for k in others), lever
        at.checkbox(key=key).check().run()
        assert not at.exception, lever
        assert at.checkbox(key=key).value is True


def test_all_levers_can_be_hidden_at_once():
    at = run_app()
    for key in SHOW.values():
        at.checkbox(key=key).uncheck()
    at.run()
    assert not at.exception
    at.slider(key="wi_ira").set_value(20_000).run()
    assert not at.exception


def test_the_marginal_rate_target_can_be_changed_and_survives_hiding_the_notes():
    at = run_app()
    assert at.selectbox(key="wi_ira_cap").value == 22
    at.selectbox(key="wi_ira_cap").set_value(12).run()
    assert not at.exception and at.session_state["wi_ira_cap"] == 12
    at.checkbox(key=SHOW["extra_ira"]).uncheck().run()
    assert not at.exception and at.session_state["wi_ira_cap"] == 12
    at.checkbox(key=SHOW["extra_ira"]).check().run()
    assert at.selectbox(key="wi_ira_cap").value == 12


def test_curves_follow_the_other_sliders_without_errors():
    at = run_app()
    at.slider(key="wi_ira").set_value(40_000).run()
    at.slider(key="wi_ltcg").set_value(60_000).run()
    at.slider(key="wi_deductions").set_value(30_000).run()
    assert not at.exception
