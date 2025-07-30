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

    # --- Mock SQLAlchemy execution ---
    mock_result = MagicMock()
    mock_result.fetchall.return_value = [
        (1, 1, 1, "2025-07-01", "Analyst")
    ]
    mock_result.keys.return_value = [
        "Reporting Week", "EmployeeID", "WorkstreamID", "WeekEnding", "Labor Category"
    ]
    mock_execute = MagicMock(return_value=mock_result)

    # --- Mock pandas.read_sql ---
    mock_df = pd.DataFrame([{
        "Reporting Week": "2025-07-01",
        "EmployeeID": 1,
        "WorkstreamID": 1,
        "WeekEnding": "2025-07-01",
        "Labor Category": "Analyst",
    }])

    # --- Mock SQLAlchemy Table with proper .c columns ---
    mock_table = MagicMock()
    mock_columns = MagicMock()
    mock_columns.EmployeeID = MagicMock()
    mock_columns.WorkstreamID = MagicMock()
    mock_table.c = mock_columns

    with patch("sqlalchemy.engine.base.Connection.execute", mock_execute), \
         patch("pandas.read_sql", MagicMock(return_value=mock_df)), \
         patch("sqlalchemy.Table", MagicMock(return_value=mock_table)):
        spec = importlib.util.spec_from_file_location("page_module", file_path)
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
        except Exception as e:
            pytest.fail(f"Failed to import {page_file}: {e}")
