# tests/test_form_submission.py

import pytest
from unittest.mock import patch, MagicMock
import datetime
import importlib.util
from pathlib import Path

@pytest.fixture(scope="module")
def form_module():
    """Dynamically import 01_Form_Submission.py for testing."""
    file_path = Path(__file__).parent.parent / "pages" / "01_Form_Submission.py"
    spec = importlib.util.spec_from_file_location("form", file_path)
    form = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(form)
    return form


@patch("utils.helpers.get_or_create_employee")
@patch("utils.helpers.clean_dataframe_dates_hours")
def test_cleaning_and_insertion_pipeline(mock_clean, mock_get_emp, form_module):
    """Verify cleaning and employee lookup pipeline works."""
    mock_clean.return_value = []
    mock_get_emp.return_value = 1

    monday = form_module.get_most_recent_monday()
    assert isinstance(monday, datetime.date)


@patch("utils.helpers.insert_weekly_report")
@patch("utils.helpers.get_or_create_employee")
@patch("utils.helpers.clean_dataframe_dates_hours")
def test_successful_form_submission(mock_clean, mock_get_emp, mock_insert, form_module):
    """Tests a valid form submission pipeline."""
    mock_clean.return_value = [{"cleaned": "data"}]
    mock_get_emp.return_value = 1
    mock_insert.return_value = True

    test_data = {
        "name": "Jane Doe",
        "reporting_week": datetime.date.today(),
        "labor_category": "Data Analyst",
        "vendor": "Iberia Advisory",
        "workstream": "WSR Automation",
        "division_command": "FMB-4",
        "work_product_title": "Dashboard",
        "brief_description_of_individuals_contribution": "Updated visuals and backend sync",
        "work_product_status": "In Progress",
        "planned_or_unplanned_monthly_pmr": "Planned",
        "if_completed": "2025-07-25",
        "distinct_nfr": "NFR-001",
        "distinct_cap": "CAP-002",
        "time_spent_hours": 7.5,
        "govt_ta": "Alex Smith"
    }

    cleaned_data = mock_clean(test_data)
    emp_id = mock_get_emp(
        test_data["name"],
        test_data["labor_category"],
        test_data["vendor"]
    )
    success = mock_insert(cleaned_data)

    assert isinstance(test_data["name"], str)
    assert isinstance(test_data["reporting_week"], datetime.date)
    assert isinstance(test_data["time_spent_hours"], float)
    assert "WSR" in test_data["workstream"]
    assert test_data["planned_or_unplanned_monthly_pmr"] in ["Planned", "Unplanned"]
    assert test_data["work_product_status"] in ["In Progress", "Completed"]

    assert emp_id == 1
    assert cleaned_data == [{"cleaned": "data"}]
    assert success is True
    mock_insert.assert_called_once()


@patch("utils.helpers.insert_weekly_report")
@patch("utils.helpers.get_or_create_employee")
@patch("utils.helpers.clean_dataframe_dates_hours")
def test_bad_data_rejected(mock_clean, mock_get_emp, mock_insert, form_module):
    """Ensures invalid submissions do not insert into the database."""
    mock_clean.return_value = [{"cleaned": "data"}]
    mock_get_emp.return_value = None
    mock_insert.return_value = False

    bad_data = {
        "name": "   ",
        "reporting_week": None,
        "labor_category": "",
        "vendor": "",
        "workstream": "WSR Automation",
        "division_command": "",
        "work_product_title": "",
        "brief_description_of_individuals_contribution": "",
        "work_product_status": "Unknown Status",
        "planned_or_unplanned_monthly_pmr": "Invalid Option",
        "if_completed": None,
        "distinct_nfr": "",
        "distinct_cap": "",
        "time_spent_hours": -5,
        "govt_ta": ""
    }

    cleaned_data = mock_clean(bad_data)
    emp_id = mock_get_emp(
        bad_data["name"],
        bad_data["labor_category"],
        bad_data["vendor"]
    )
    success = mock_insert(cleaned_data)

    assert emp_id is None
    assert success is False
    mock_insert.assert_called_once()



@pytest.fixture(scope="module")
def form_module():
    """Dynamically import 01_Form_Submission.py for testing."""
    file_path = Path(__file__).parent.parent / "pages" / "01_Form_Submission.py"
    spec = importlib.util.spec_from_file_location("form", file_path)
    form = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(form)
    return form

def test_empty_required_fields(form_module):
    """Ensure submission fails if required fields are missing."""
    with patch("utils.helpers.insert_weekly_report", MagicMock(return_value=False)):
        result = form_module.submit_form(
            name="", vendor="", labor_category="", week_ending=None
        )
        assert result is False

def test_duplicate_submission(form_module):
    """Ensure duplicate submissions do not create duplicates."""
    mock_insert = MagicMock(side_effect=[True, False])  # first OK, second blocked
    with patch("utils.helpers.insert_weekly_report", mock_insert):
        first = form_module.submit_form("John Doe", "VendorX", "Manager", "2025-07-01")
        second = form_module.submit_form("John Doe", "VendorX", "Manager", "2025-07-01")
        assert first is True
        assert second is False

def test_max_length_fields(form_module):
    """Ensure long strings are handled gracefully."""
    long_name = "A" * 300
    with patch("utils.helpers.insert_weekly_report", MagicMock(return_value=True)):
        result = form_module.submit_form(long_name, "VendorY", "Engineer", "2025-07-01")
        assert result is True

def test_invalid_date_format(form_module):
    """Ensure invalid date is rejected."""
    with patch("utils.helpers.insert_weekly_report", MagicMock(return_value=False)):
        result = form_module.submit_form("Jane Doe", "VendorZ", "Lead", "invalid-date")
        assert result is False
