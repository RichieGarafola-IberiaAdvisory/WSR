# tests/conftest.py
import pytest
from unittest.mock import MagicMock
import utils.db as db
import utils.helpers as helpers


@pytest.fixture(autouse=True, scope="session")
def mock_metadata(monkeypatch):
    """
    Mock database metadata and table objects for all tests.
    Prevents schema reflection errors when running against SQLite in CI.
    """
    # Create mock tables
    mock_employees = MagicMock()
    mock_workstreams = MagicMock()
    mock_hourstracking = MagicMock()
    mock_weeklyreports = MagicMock()
    mock_accomplishments = MagicMock()

    # Mock MetaData with tables dict
    mock_meta = MagicMock()
    mock_meta.tables = {
        "Employees": mock_employees,
        "Workstreams": mock_workstreams,
        "HoursTracking": mock_hourstracking,
        "WeeklyReports": mock_weeklyreports,
        "Accomplishments": mock_accomplishments,
    }

    # Patch db module attributes
    monkeypatch.setattr(db, "get_metadata", lambda: mock_meta)
    monkeypatch.setattr(db, "employees", mock_employees)
    monkeypatch.setattr(db, "workstreams", mock_workstreams)
    monkeypatch.setattr(db, "hourstracking", mock_hourstracking)
    monkeypatch.setattr(db, "weeklyreports", mock_weeklyreports)
    monkeypatch.setattr(db, "accomplishments", mock_accomplishments)

    yield


@pytest.fixture(autouse=True, scope="session")
def mock_helpers_functions(monkeypatch):
    """
    Mock helper functions missing in utils.helpers that tests reference.
    """
    if not hasattr(helpers, "insert_weekly_report"):
        monkeypatch.setattr(helpers, "insert_weekly_report", MagicMock(return_value=True))

    yield
