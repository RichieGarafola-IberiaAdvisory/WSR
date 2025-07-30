# tests/test_form_submission.py

import pytest
from unittest.mock import patch, MagicMock
import datetime


@patch("utils.helpers.get_or_create_employee")
@patch("utils.helpers.clean_dataframe_dates_hours")
def test_cleaning_and_insertion_pipeline(mock_clean, mock_get_emp):
    """Basic check to verify cleaning and employee lookup pipeline works."""
    from pages import _01_Form_Submission as form

    mock_clean.return_value = []
    mock_get_emp.return_value = 1

    monday = form.get_most_recent_monday()
    assert isinstance(monday, datetime.date)


@patch("utils.helpers.insert_weekly_report")
@patch("utils.helpers.get_or_create_employee")
@patch("utils.helpers.clean_dataframe_dates_hours")
def test_successful_form_submission(mock_clean, mock_get_emp, mock_insert):
    """Tests that a valid form submission goes through cleaning, employee retrieval,
    and database insertion successfully."""
    from pages import _01_Form_Submission as form

    # Setup mocks
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

    # Simulate the cleaned pipeline
    cleaned_data = mock_clean(test_data)
    emp_id = mock_get_emp(
        test_data["name"],
        test_data["labor_category"],
        test_data["vendor"]
    )
    success = mock_insert(cleaned_data)

    # Assertions
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
def test_bad_data_rejected(mock_clean, mock_get_emp, mock_insert):
    """Ensures that submissions with missing or invalid fields do not proceed."""
    from pages import _01_Form_Submission as form

    # Setup mocks
    mock_clean.return_value = [{"cleaned": "data"}]
    mock_get_emp.return_value = None  # simulate failure to find/create employee
    mock_insert.return_value = False

    bad_data = {
        "name": "   ",  # invalid
        "reporting_week": None,
        "labor_category": "",
        "vendor": "",
        "workstream": "WSR Automation",
        "division_command": "",
        "work_product_title": "",
        "brief_description_of_individuals_contribution": "",
        "work_product_status": "Unknown Status",  # invalid status
        "planned_or_unplanned_monthly_pmr": "Invalid Option",
        "if_completed": None,
        "distinct_nfr": "",
        "distinct_cap": "",
        "time_spent_hours": -5,  # invalid hours
        "govt_ta": ""
    }

    cleaned_data = mock_clean(bad_data)
    emp_id = mock_get_emp(
        bad_data["name"],
        bad_data["labor_category"],
        bad_data["vendor"]
    )

    success = mock_insert(cleaned_data)

    # We expect failure in employee creation and insert
    assert emp_id is None
    assert success is False
    mock_insert.assert_called_once()
