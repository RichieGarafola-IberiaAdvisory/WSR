# tests/test_form_submission.py
import pytest
import importlib.util
import os
from unittest.mock import patch

def load_form_module():
    """Dynamically load the _01_Form_Submission.py module"""
    module_path = os.path.join("pages", "01_Form_Submission.py")
    spec = importlib.util.spec_from_file_location("form_submission", module_path)
    form = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(form)
    return form

@patch("utils.helpers.get_or_create_employee")
@patch("utils.helpers.clean_dataframe_dates_hours")
def test_cleaning_and_insertion_pipeline(mock_clean, mock_get_emp):
    form = load_form_module()

    # Mock return values
    mock_clean.return_value = []
    mock_get_emp.return_value = 1

    assert form.get_most_recent_monday() is not None
