# tests/test_db.py
import pytest
from utils import db
import sqlalchemy.exc

def test_get_engine_returns_engine():
    engine = db.get_engine()
    assert engine is not None
    assert hasattr(engine, 'connect')

def test_get_metadata_returns_metadata():
    try:
        metadata = db.get_metadata()
        assert metadata is not None
        assert hasattr(metadata, 'tables')
    except sqlalchemy.exc.OperationalError:
        pytest.skip("Database not available in CI")

def test_get_table_known():
    try:
        table = db.get_table("employees")
        assert table is not None
        assert "employeeid" in table.c
    except (sqlalchemy.exc.OperationalError, KeyError):
        pytest.skip("Database or table not available in CI")

def test_get_table_unknown_raises():
    try:
        db.get_table("nonexistent_table")
        pytest.fail("Expected KeyError not raised")
    except KeyError:
        pass  # expected
    except sqlalchemy.exc.OperationalError:
        pytest.skip("Database not available in CI")
