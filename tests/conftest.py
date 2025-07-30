import pytest
from unittest.mock import MagicMock
import utils.db as db

@pytest.fixture(autouse=True)
def mock_metadata(monkeypatch):
    """Mock database metadata and tables for all tests."""
    mock_meta = MagicMock()
    mock_meta.tables = {
        "Employees": MagicMock(),
        "Workstreams": MagicMock()
    }
    monkeypatch.setattr(db, "get_metadata", lambda: mock_meta)

    # Mock table objects
    db.employees = MagicMock()
    db.workstreams = MagicMock()
    db.hourstracking = MagicMock()
    yield
