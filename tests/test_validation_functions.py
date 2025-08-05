# tests/test_validation_functions.py
import pandas as pd
from pages.01_Form_Submission import validate_accomplishments

def test_exceeding_accomplishments_flagged():
    df = pd.DataFrame([{
        "contractorname": "Jane Doe",
        "weekstartdate": "2025-08-05",
        **{f"accomplishment{i}": "Task" for i in range(1, 8)}  # 7 entries
    }])
    invalid = validate_accomplishments(df)
    assert not invalid.empty
