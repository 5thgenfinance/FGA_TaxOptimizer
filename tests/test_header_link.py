from pathlib import Path

from app.config import REPO_ROOT

SOURCE = Path(REPO_ROOT, "streamlit_app.py").read_text(encoding="utf-8")


def test_the_header_button_serves_the_excel_file_stored_in_the_repository():
    assert 'EXCEL_LABEL = "Download Excel Version"' in SOURCE
    assert 'EXCEL_FILE = REPO_ROOT / "TaxRetirementOptimizer.xlsx"' in SOURCE
    assert "download_button(EXCEL_LABEL" in SOURCE
    assert "dropbox" not in SOURCE.lower()


def test_the_excel_file_exists_in_the_repository():
    workbook = Path(REPO_ROOT, "TaxRetirementOptimizer.xlsx")
    assert workbook.is_file() and workbook.stat().st_size > 0


def test_the_button_sits_inside_the_header_band():
    header = SOURCE.index('st.container(key="fga_header")')
    button = SOURCE.index("download_button(EXCEL_LABEL")
    assert header < button < SOURCE.index("def _handle_import")
