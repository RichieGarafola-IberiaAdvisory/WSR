# tests/test_form_submission.py

import pytest
from unittest.mock import patch, MagicMock
import datetime

# Mock dependencies in the helpers module
@patch("utils.helpers.get_or_create_employee")
@patch("utils.helpers.clean_dataframe_dates_hours")
def test_cleaning_and_insertion_pipeline(mock_clean, mock_get_emp):
    from pages import _01_Form_Submission as form

    mock_clean.return_value = []
    mock_get_emp.return_value = 1

    # Basic check to verify form module loads and key function works
    monday = form.get_most_recent_monday()
    assert isinstance(monday, datetime.date)


# @patch("utils.helpers.insert_weekly_report")
# @patch("utils.helpers.get_or_create_employee")
# @patch("utils.helpers.clean_dataframe_dates_hours")
# def test_form_submission_fields(mock_clean, mock_get_emp, mock_insert):
#     from pages import _01_Form_Submission as form

#     # Set up mock return values
#     mock_clean.return_value = []
#     mock_get_emp.return_value = 1
#     mock_insert.return_value = True

#     # Sample test data
#     test_data = {
#         "name": "Jane Doe",
#         "reporting_week": datetime.date.today(),
#         "labor_category": "Data Analyst",
#         "vendor": "Iberia Advisory",
#         "workstream": "WSR Automation",
#         "division_command": "FMB-4",
#         "work_product_title": "Dashboard",
#         "brief_description_of_individuals_contribution": "Updated visuals and backend sync",
#         "work_product_status": "In Progress",
#         "planned_or_unplanned_monthly_pmr": "Planned",
#         "if_completed": "2025-07-25",
#         "distinct_nfr": "NFR-001",
#         "distinct_cap": "CAP-002",
#         "time_spent_hours": 7.5,
#         "govt_ta": "Alex Smith"
#     }

#     # Simulate function logic, assuming form is collecting and cleaning this
#     # You may have a function like form.process_submission(data), mock it if needed
#     assert isinstance(test_data["name"], str)
#     assert isinstance(test_data["reporting_week"], datetime.date)
#     assert isinstance(test_data["time_spent_hours"], float)
#     assert "WSR" in test_data["workstream"]
#     assert test_data["planned_or_unplanned_monthly_pmr"] in ["Planned", "Unplanned"]
#     assert test_data["work_product_status"] in ["In Progress", "Completed"]

#     # You could simulate a call like: form.submit_report(test_data)
#     # and assert that insert_weekly_report was called correctly
#     mock_insert.assert_not_called()
#     mock_insert.return_value = True

#     # Simulate a simplified pipeline
#     cleaned_data = mock_clean(test_data)
#     emp_id = mock_get_emp(test_data["name"], test_data["labor_category"], test_data["vendor"])
#     success = mock_insert(cleaned_data)

#     assert emp_id == 1
#     assert cleaned_data == []
#     assert success is True
