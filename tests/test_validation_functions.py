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


def test_exceeding_accomplishments_flagged(form_module):
    """Test that more than 5 accomplishments (split across rows) are flagged."""
    df = pd.DataFrame([
        {
            "contractorname": "Jane Doe",
            "weekstartdate": "2025-08-05",
            **{f"accomplishment{i}": "Task" for i in range(1, 5 + 1)}
        },
        {
            "contractorname": "Jane Doe",
            "weekstartdate": "2025-08-05",
            "accomplishment1": "Extra Task"
        }
    ])
    invalid = form_module.validate_accomplishments(df)
    assert not invalid.empty
