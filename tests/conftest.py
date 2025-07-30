import pytest
from sqlalchemy import create_engine
from utils import db

@pytest.fixture(scope="session")
def engine():
    return db.get_engine()

@pytest.fixture
def mock_connection(monkeypatch):
    conn = create_engine("sqlite:///:memory:")
    monkeypatch.setattr(db, "get_engine", lambda: conn)
    return conn
