import pytest
from unittest.mock import MagicMock
import utils.db as db
import utils.helpers as helpers
from sqlalchemy import Table, Column, Integer, String, DateTime, Float, MetaData, ForeignKey


@pytest.fixture(autouse=True, scope="session")
def patch_db_metadata():
    """Mock DB metadata and tables with real SQLAlchemy Table objects."""
    mock_meta = MetaData()

    # Employees Table
    employees_table = Table(
        "Employees", mock_meta,
        Column("EmployeeID", Integer, primary_key=True),
        Column("UniqueKey", String),
        Column("VendorName", String),
        Column("LaborCategory", String),
    )

    # Workstreams Table
    workstreams_table = Table(
        "Workstreams", mock_meta,
        Column("WorkstreamID", Integer, primary_key=True),
        Column("Name", String),
    )

    # WeeklyReports Table
    weekly_reports_table = Table(
        "WeeklyReports", mock_meta,
        Column("ReportID", Integer, primary_key=True),
        Column("EmployeeID", Integer, ForeignKey("Employees.EmployeeID")),
        Column("WorkstreamID", Integer, ForeignKey("Workstreams.WorkstreamID")),
        Column("WeekEnding", DateTime),
    )

    # Accomplishments Table
    accomplishments_table = Table(
        "Accomplishments", mock_meta,
        Column("AccomplishmentID", Integer, primary_key=True),
        Column("ReportID", Integer, ForeignKey("WeeklyReports.ReportID")),
        Column("Description", String),
    )

    # HoursTracking Table
    hours_tracking_table = Table(
        "HoursTracking", mock_meta,
        Column("HoursID", Integer, primary_key=True),
        Column("EmployeeID", Integer, ForeignKey("Employees.EmployeeID")),
        Column("WeekEnding", DateTime),
        Column("HoursWorked", Float),
    )

    # Attach to db module
    db.employees = employees_table
    db.workstreams = workstreams_table
    db.weekly_reports = weekly_reports_table
    db.accomplishments = accomplishments_table
    db.hours_tracking = hours_tracking_table

    db._metadata = mock_meta
    db.get_metadata = lambda: mock_meta

    return mock_meta


@pytest.fixture(autouse=True, scope="session")
def patch_helpers_functions():
    """Add missing helper functions for tests."""
    if not hasattr(helpers, "insert_weekly_report"):
        setattr(helpers, "insert_weekly_report", MagicMock(return_value=True))
    return helpers


@pytest.fixture(autouse=True, scope="function")
def mock_sqlalchemy_execute(monkeypatch):
    """Mock SQLAlchemy execute for select, insert, and update queries."""

    def fake_execute(self, query, *args, **kwargs):
        q = str(query).lower()

        # --- Employees ---
        # First SELECT call for existing employee
        if "employees" in q and "select" in q:
            called = getattr(self, "_emp_called", 0)
            self._emp_called = called + 1
            if called == 0:
                return MagicMock(mappings=lambda: MagicMock(fetchone=lambda: {
                    "EmployeeID": 1,
                    "VendorName": "",
                    "LaborCategory": "Unknown LCAT"
                }))
            else:
                # Second call = update executed
                return MagicMock()

        # Insert employee
        if "employees" in q and "insert" in q:
            return MagicMock(scalar_one=lambda: 5)

        # --- Workstreams ---
        if "workstreams" in q and "select" in q:
            called = getattr(self, "_ws_called", 0)
            self._ws_called = called + 1
            if called == 0:
                return MagicMock(scalar_one_or_none=lambda: 3)
            else:
                return MagicMock()

        if "workstreams" in q and "insert" in q:
            return MagicMock(scalar_one=lambda: 7)

        # --- Default insert/update ---
        if "insert" in q:
            return MagicMock(scalar_one=lambda: 99)

        return MagicMock()

    monkeypatch.setattr("sqlalchemy.engine.base.Connection.execute", fake_execute)
    yield
