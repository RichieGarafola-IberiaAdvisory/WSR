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

def test_validate_accomplishments_with_extra_entries(form_module):
    """Test that exactly 5 accomplishments passes validation."""
    df = pd.DataFrame([{
        "contractorname": "John Doe",
        "weekstartdate": "2025-08-05",
        **{f"accomplishment{i}": "Task" for i in range(1, 6)}
    }])
    invalid = form_module.validate_accomplishments(df)
    assert invalid.empty  # Should pass with exactly 5

def test_validate_accomplishments_with_missing_entries(form_module):
    """Test that fewer than 5 accomplishments fails validation."""
    df = pd.DataFrame([{
        "contractorname": "John Doe",
        "weekstartdate": "2025-08-05",
        "accomplishment1": "Task"
        # Missing accomplishments 2-5
    }])
    invalid = form_module.validate_accomplishments(df)
    assert not invalid.empty
