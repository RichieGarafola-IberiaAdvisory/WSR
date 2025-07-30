import pytest
import importlib.util
from pathlib import Path
from unittest.mock import patch, MagicMock
import pandas as pd

PAGES_DIR = Path(__file__).parent.parent / "pages"
PAGE_FILES = [
    "01_Form_Submission.py",
    "02_Management_Dashboard.py",
    "03_HR_KPIs.py",
    "04_Accomplishments_Dashboard.py",
]

@pytest.mark.parametrize("page_file", PAGE_FILES)
def test_page_imports(page_file):
    """Smoke test: ensure each Streamlit page loads without DB/data errors."""
    file_path = PAGES_DIR / page_file

    # Mock DB execution
    mock_execute = MagicMock(return_value=MagicMock(
        fetchall=lambda: [(1, 1, 1, "2025-07-01", "Analyst")],
        mappings=lambda: MagicMock(fetchone=lambda: {"EmployeeID": 1}),
        scalar_one_or_none=lambda: 1,
    ))

    # ✅ Non-empty DataFrame with expected columns
    mock_df = pd.DataFrame([{
        "Reporting Week": "2025-07-01",
        "EmployeeID": 1,
        "WorkstreamID": 1,
        "WeekEnding": "2025-07-01",
        "Labor Category": "Analyst",
    }])

    with patch("sqlalchemy.engine.base.Connection.execute", mock_execute), \
         patch("pandas.read_sql", MagicMock(return_value=mock_df)):
        spec = importlib.util.spec_from_file_location("page_module", file_path)
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
        except Exception as e:
            pytest.fail(f"Failed to import {page_file}: {e}")
