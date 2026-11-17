import shutil
from decimal import Decimal
from pathlib import Path

import pytest

from app.config import DATA_DIR
from app.tables import TableValidationError, is_unbounded, load_all


@pytest.fixture()
def data_copy(tmp_path: Path) -> Path:
    dest = tmp_path / "data"
    shutil.copytree(DATA_DIR, dest)
    return dest


def _edit(path: Path, fn):
    path.write_text(fn(path.read_text(encoding="utf-8")), encoding="utf-8")


def test_real_data_loads():
    t = load_all()
    assert len(t.rows("tblTaxRate")) == 21
    assert len(t.rows("tblTaxRateLTCG")) == 9
    assert len(t.rows("tblUniformRMDFactors")) == 49
    assert len(t.rows("tblStandDeductionBase")) == 6
    assert len(t.rows("tblAMT")) == 6
    assert len(t.rows("tblNIIT")) == 6
    assert len(t.rows("tblInputMap")) == 21


def test_supported_years():
    assert load_all().supported_years() == [2026, 2027]


def test_no_warnings_when_every_year_has_a_top_bracket():
    assert load_all().warnings == ()


def test_known_values():
    t = load_all()
    rmd = {r.Age: r.LifeExpectancyFactor for r in t.rows("tblUniformRMDFactors")}
    assert rmd[72] == Decimal("27.4") and rmd[74] == Decimal("25.5") and rmd[120] == Decimal("2")
    amt = {(r.Year, r.Status): r for r in t.rows("tblAMT")}
    assert amt[(2026, "Jointly")].Exemption == Decimal("140200")
    assert amt[(2027, "Single")].Exemption == Decimal("93000")


def test_input_map_is_ordered():
    orders = [r.Order for r in load_all().rows("tblInputMap")]
    assert orders == sorted(orders) == list(range(1, 22))


def test_warns_when_top_bracket_is_missing(data_copy):
    _edit(data_copy / "tblTaxRate.csv", lambda s: s.replace("2026,7,9999999,9999999,0.37\n", ""))
    warnings = load_all(data_copy).warnings
    assert any("tblTaxRate.csv 2026" in w for w in warnings)


def test_sentinel_detection():
    assert is_unbounded(Decimal("9999999"))
    assert is_unbounded(Decimal("999999999"))
    assert not is_unbounded(Decimal("640600"))


def test_duplicate_key_fails(data_copy):
    _edit(data_copy / "tblNIIT.csv", lambda s: s + "2026,Single,1\n")
    with pytest.raises(TableValidationError, match="duplicate key"):
        load_all(data_copy)


def test_unsorted_limits_fail(data_copy):
    _edit(data_copy / "tblTaxRate.csv", lambda s: s.replace("2026,2,50400", "2026,2,12000"))
    with pytest.raises(TableValidationError, match="must ascend"):
        load_all(data_copy)


def test_bucket_order_fails(data_copy):
    _edit(data_copy / "tblTaxRateLTCG.csv", lambda s: s.replace("2026,2,", "2026,5,"))
    with pytest.raises(TableValidationError, match="buckets must be"):
        load_all(data_copy)


def test_header_mismatch_fails(data_copy):
    _edit(data_copy / "tblStandDeductionBase.csv", lambda s: s.replace("FilingYear", "Year", 1))
    with pytest.raises(TableValidationError, match="header"):
        load_all(data_copy)


def test_missing_file_fails(data_copy):
    (data_copy / "tblAMT.csv").unlink()
    with pytest.raises(TableValidationError, match="file not found"):
        load_all(data_copy)


def test_amt_end_not_after_start_fails(data_copy):
    _edit(data_copy / "tblAMT.csv", lambda s: s.replace("500000,680200", "500000,500000", 1))
    with pytest.raises(TableValidationError, match="End must be greater"):
        load_all(data_copy)


def test_rate_out_of_range_fails(data_copy):
    _edit(data_copy / "tblTaxRate.csv", lambda s: s.replace("2026,1,12400,24800,0.10", "2026,1,12400,24800,1.5"))
    with pytest.raises(TableValidationError):
        load_all(data_copy)


def test_rmd_gap_fails(data_copy):
    _edit(data_copy / "tblUniformRMDFactors.csv", lambda s: s.replace("80,20.2\n", ""))
    with pytest.raises(TableValidationError, match="contiguous"):
        load_all(data_copy)


def test_input_map_unknown_field_fails(data_copy):
    _edit(data_copy / "tblInputMap.csv", lambda s: s.replace("wages_and_tips", "wages_typo"))
    with pytest.raises(TableValidationError, match="not on FilerInputs"):
        load_all(data_copy)
