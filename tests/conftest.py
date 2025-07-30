# tests/conftest.py

import pytest
from unittest.mock import MagicMock
from sqlalchemy.sql import Select
import utils.db as db
import utils.helpers as helpers

@pytest.fixture(autouse=True, scope="function")  # was session
def mock_metadata(monkeypatch):
    """Mock database metadata and table objects for all tests."""
    mock_employees = MagicMock()
    mock_workstreams = MagicMock()
    mock_hourstracking = MagicMock()
    mock_weeklyreports = MagicMock()
    mock_accomplishments = MagicMock()

    mock_meta = MagicMock()
    mock_meta.tables = {
        "Employees": mock_employees,
        "Workstreams": mock_workstreams,
        "HoursTracking": mock_hourstracking,
        "WeeklyReports": mock_weeklyreports,
        "Accomplishments": mock_accomplishments,
    }

    monkeypatch.setattr(db, "get_metadata", lambda: mock_meta)
    monkeypatch.setattr(db, "employees", mock_employees)
    monkeypatch.setattr(db, "workstreams", mock_workstreams)
    monkeypatch.setattr(db, "hourstracking", mock_hourstracking)
    monkeypatch.setattr(db, "weeklyreports", mock_weeklyreports)
    monkeypatch.setattr(db, "accomplishments", mock_accomplishments)

    yield


@pytest.fixture(autouse=True, scope="function")  # was session
def mock_helpers_functions(monkeypatch):
    """Mock helper functions missing in utils.helpers that tests reference."""
    if not hasattr(helpers, "insert_weekly_report"):
        monkeypatch.setattr(helpers, "insert_weekly_report", MagicMock(return_value=True))
    yield


@pytest.fixture(autouse=True, scope="function")  # was session
def mock_sqlalchemy_select(monkeypatch):
    """Mock SQLAlchemy select execution in helpers to avoid real DB access."""
    def fake_execute(self, query, *args, **kwargs):
        query_str = str(query).lower()
        if "employees" in query_str and "select" in query_str:
            return MagicMock(mappings=lambda: MagicMock(fetchone=lambda: {"EmployeeID": 1}))
        if "workstreams" in query_str and "select" in query_str:
            return MagicMock(scalar_one_or_none=lambda: 3)
        if "insert" in query_str:
            return MagicMock(scalar_one=lambda: 5)
        return MagicMock()

    monkeypatch.setattr("sqlalchemy.engine.base.Connection.execute", fake_execute)
    yield
