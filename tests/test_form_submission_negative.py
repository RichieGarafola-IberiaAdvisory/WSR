import pytest
import pandas as pd
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

def test_missing_required_fields_blocks_submission(form_module):
    """Ensure that completely missing required fields blocks submission."""
    df = pd.DataFrame([{
        "Contractor (Last, First Name)": "",
        "Vendor Name": "",
        "Labor Category": "",
        "Workstream": ""
    }])
    assert not form_module.has_required_fields(df)

def test_partial_required_fields_allows_submission(form_module):
    """Ensure that missing at least one required field still blocks submission."""
    df = pd.DataFrame([{
        "Contractor (Last, First Name)": "Doe, John",
        "Vendor Name": "Iberia",
        "Labor Category": "Analyst",
        "Workstream": ""  # Missing
    }])
    assert not form_module.has_required_fields(df)
