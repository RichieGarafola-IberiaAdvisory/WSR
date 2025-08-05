# tests/test_form_submission_negative.py
import pytest
from pages.01_Form_Submission import has_required_fields
import pandas as pd

def test_missing_required_fields_blocks_submission():
    df = pd.DataFrame([{
        "Contractor (Last, First Name)": "",
        "Vendor Name": "",
        "Labor Category": "",
        "Workstream": ""
    }])
    assert not has_required_fields(df)

def test_partial_required_fields_allows_submission():
    df = pd.DataFrame([{
        "Contractor (Last, First Name)": "Doe, John",
        "Vendor Name": "Iberia",
        "Labor Category": "Analyst",
        "Workstream": ""
    }])
    assert not has_required_fields(df)
