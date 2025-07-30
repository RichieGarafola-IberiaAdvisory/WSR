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

    # Mock DB and pandas calls to avoid real queries and missing columns
    with patch("utils.db.get_db_connection", MagicMock()), \
         patch("sqlalchemy.engine.base.Connection.execute",
               MagicMock(return_value=MagicMock(
                   fetchall=lambda: [],
                   mappings=lambda: MagicMock(fetchone=lambda: None)
               ))), \
         patch("pandas.read_sql",
               MagicMock(return_value=pd.DataFrame(columns=[
                   "Reporting Week", "EmployeeID", "WorkstreamID"
               ]))):
        spec = importlib.util.spec_from_file_location("page_module", file_path)
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
        except Exception as e:
            pytest.fail(f"Failed to import {page_file}: {e}")
