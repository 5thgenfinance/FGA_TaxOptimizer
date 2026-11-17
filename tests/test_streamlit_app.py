from pathlib import Path

import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest  # noqa: E402

APP = str(Path(__file__).resolve().parent.parent / "streamlit_app.py")


def test_app_runs_without_exception():
    at = AppTest.from_file(APP, default_timeout=30).run()
    assert not at.exception
