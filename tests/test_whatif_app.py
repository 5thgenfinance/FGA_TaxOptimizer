from pathlib import Path

import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest  # noqa: E402

from app import whatif  # noqa: E402

APP = str(Path(__file__).resolve().parent.parent / "streamlit_app.py")


def run_app() -> AppTest:
    return AppTest.from_file(APP, default_timeout=30).run()


def test_the_whatif_tab_runs_with_no_adjustment():
    at = run_app()
    assert not at.exception
    for key in whatif.SLIDER_KEYS.values():
        assert at.slider(key=key).value == 0


def test_moving_each_slider_recalculates_without_errors():
    at = run_app()
    for key, value in ("wi_ltcg", 20_000), ("wi_stcg", -5_000), ("wi_deductions", 10_000), ("wi_ira", 25_000):
        at.slider(key=key).set_value(value).run()
        assert not at.exception, key
        assert at.session_state[key] == value


def test_the_sliders_do_not_change_the_real_inputs():
    at = run_app()
    before = {k: v for k, v in at.session_state.filtered_state.items() if k.startswith("in_")}
    at.slider(key="wi_ira").set_value(50_000).run()
    after = {k: v for k, v in at.session_state.filtered_state.items() if k.startswith("in_")}
    assert before == after


def test_reset_returns_every_slider_to_zero():
    at = run_app()
    at.slider(key="wi_ira").set_value(25_000).run()
    at.slider(key="wi_ltcg").set_value(-10_000).run()
    at.button(key="wi_reset").click().run()
    assert not at.exception
    assert all(at.session_state[key] == 0 for key in whatif.SLIDER_KEYS.values())
