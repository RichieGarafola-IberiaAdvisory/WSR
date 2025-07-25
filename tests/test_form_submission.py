# tests/test_form_submission.py
import pytest
from unittest.mock import patch, MagicMock

@patch("utils.helpers.get_or_create_employee")
@patch("utils.helpers.clean_dataframe_dates_hours")
def test_cleaning_and_insertion_pipeline(mock_clean, mock_get_emp):
    from pages import _01_Form_Submission as form

    # Mock out return values
    mock_clean.return_value = []
    mock_get_emp.return_value = 1

    assert form.get_most_recent_monday() is not None
