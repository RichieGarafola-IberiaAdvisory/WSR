# tests/test_db.py
import pytest
from utils import db

def test_get_engine_returns_engine():
    engine = db.get_engine()
    assert engine is not None
    assert hasattr(engine, 'connect')

def test_get_metadata_returns_metadata():
    metadata = db.get_metadata()
    assert metadata is not None
    assert hasattr(metadata, 'tables')

def test_get_table_known():
    table = db.get_table("employees")
    assert table is not None
    assert "employeeid" in table.c

def test_get_table_unknown_raises():
    with pytest.raises(KeyError):
        db.get_table("nonexistent_table")
