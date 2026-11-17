import pytest

from app.calc.common import UnknownStatusError
from app.status import normalize_status


@pytest.mark.parametrize("raw,expected", [
    ("Single", "Single"), (" s ", "Single"), ("JOINTLY", "Jointly"), ("MFJ", "Jointly"),
    ("Married Filing Jointly", "Jointly"), ("mfs", "Separate"), ("Separate", "Separate"),
])
def test_aliases(tables, raw, expected):
    assert normalize_status(raw, tables) == expected


def test_unknown_status(tables):
    with pytest.raises(UnknownStatusError):
        normalize_status("head of household", tables)
