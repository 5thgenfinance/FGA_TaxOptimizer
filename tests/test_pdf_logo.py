from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app import pdf_report

pytest.importorskip("reportlab")


@pytest.fixture()
def image(tmp_path):
    PIL = pytest.importorskip("PIL.Image")
    path = tmp_path / "logo.jpg"
    PIL.new("RGB", (400, 100), (26, 39, 68)).save(path)
    return path


def test_logo_is_scaled_proportionally(image):
    flowable = pdf_report.logo_flowable(image, 200)
    assert flowable is not None
    assert flowable.drawWidth == 200 and flowable.drawHeight == 50


def test_missing_or_broken_logo_is_ignored(tmp_path):
    assert pdf_report.logo_flowable(None, 100) is None
    assert pdf_report.logo_flowable(tmp_path / "missing.jpg", 100) is None
    broken = tmp_path / "broken.jpg"
    broken.write_bytes(b"not an image")
    assert pdf_report.logo_flowable(broken, 100) is None


def test_pdf_builds_with_and_without_logo(tables, image):
    from app.calc.engine import compute
    from app.models import FilerInputs
    inputs = FilerInputs(tax_year=2026, filing_status="Single", dob=date(1960, 1, 1), wages_and_tips=80_000)
    result = compute(inputs, tables)
    plain = pdf_report.build_pdf(result, inputs, tables, "T", "2026-11-16T10:00:00", now=datetime(2026, 11, 16))
    branded = pdf_report.build_pdf(result, inputs, tables, "T", "2026-11-16T10:00:00",
                                   now=datetime(2026, 11, 16), logo=image)
    assert plain.startswith(b"%PDF") and branded.startswith(b"%PDF")
    assert len(branded) > len(plain)
