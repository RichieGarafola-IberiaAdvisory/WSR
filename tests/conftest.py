import pytest
from unittest.mock import MagicMock
import utils.db as db
import utils.helpers as helpers

@pytest.fixture(autouse=True, scope="session")
def patch_db_metadata():
    """Prevent DB reflection by mocking metadata."""
    mock_meta = MagicMock()
    mock_meta.tables = {
        "Employees": MagicMock(),
        "Workstreams": MagicMock(),
        "HoursTracking": MagicMock(),
        "WeeklyReports": MagicMock(),
        "Accomplishments": MagicMock(),
    }
    setattr(db, "_metadata", mock_meta)
    setattr(db, "get_metadata", lambda: mock_meta)
    return mock_meta

@pytest.fixture(autouse=True, scope="session")
def patch_helpers_functions():
    """Add missing helper functions for tests."""
    if not hasattr(helpers, "insert_weekly_report"):
        setattr(helpers, "insert_weekly_report", MagicMock(return_value=True))
    return helpers

@pytest.fixture(autouse=True, scope="function")
def mock_sqlalchemy_execute(monkeypatch):
    """Mock SQLAlchemy execute for select and insert queries."""
    def fake_execute(self, query, *args, **kwargs):
        q = str(query).lower()
        if "employees" in q and "select" in q:
            return MagicMock(mappings=lambda: MagicMock(fetchone=lambda: {"EmployeeID": 1}))
        if "workstreams" in q and "select" in q:
            return MagicMock(scalar_one_or_none=lambda: 3)
        if "insert" in q:
            return MagicMock(scalar_one=lambda: 5)
        return MagicMock()

    monkeypatch.setattr("sqlalchemy.engine.base.Connection.execute", fake_execute)
    yield
