# tests/test_form_submission_edge_cases.py
import pytest
import pandas as pd
from pages.01_Form_Submission import validate_accomplishments

def test_validate_accomplishments_with_extra_entries():
    df = pd.DataFrame([{
        "contractorname": "John Doe",
        "weekstartdate": "2025-08-05",
        **{f"accomplishment{i}": "Task" for i in range(1, 6)}
    }])
    invalid = validate_accomplishments(df)
    assert invalid.empty  # Should pass with exactly 5

def test_validate_accomplishments_with_missing_entries():
    df = pd.DataFrame([{
        "contractorname": "John Doe",
        "weekstartdate": "2025-08-05",
        "accomplishment1": "Task"
        # Missing the other accomplishments
    }])
    invalid = validate_accomplishments(df)
    assert not invalid.empty
