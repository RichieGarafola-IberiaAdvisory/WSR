import pytest
from unittest.mock import MagicMock
import utils.db as db
import utils.helpers as helpers

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



@pytest.fixture(autouse=True)
def mock_helpers(monkeypatch):
    if not hasattr(helpers, "insert_weekly_report"):
        monkeypatch.setattr(helpers, "insert_weekly_report", MagicMock(return_value=True))
    yield

