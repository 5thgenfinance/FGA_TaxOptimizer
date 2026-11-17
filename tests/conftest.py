import pytest

from app.tables import load_all


@pytest.fixture(scope="session")
def tables():
    return load_all()
