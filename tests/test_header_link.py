from pathlib import Path

from app.config import REPO_ROOT

SOURCE = Path(REPO_ROOT, "streamlit_app.py").read_text(encoding="utf-8")


def test_the_header_has_the_excel_download_button_with_the_dropbox_link():
    assert 'EXCEL_LABEL = "Download Excel Version"' in SOURCE
    assert "https://www.dropbox.com/scl/fi/lri563e388sae3oecgjsu/TaxRetirementOptimizer.xltx" in SOURCE
    assert "rlkey=ytpzvkcrkto7ctl5ap54ttkry" in SOURCE
    assert "link_button(EXCEL_LABEL, EXCEL_URL" in SOURCE


def test_the_button_sits_inside_the_header_band():
    header = SOURCE.index('st.container(key="fga_header")')
    button = SOURCE.index("link_button(EXCEL_LABEL")
    assert header < button < SOURCE.index("def _handle_import")
