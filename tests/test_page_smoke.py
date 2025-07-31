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

    # Mock database fetch
    mock_result = MagicMock()
    mock_result.fetchall.return_value = [
        (1, 1, 1, "2025-07-01", "Analyst", "50%", "Vendor A", 40)
    ]
    mock_result.keys.return_value = [
        "Reporting Week", "ReportID", "EmployeeID", "WorkstreamID",
        "WeekEnding", "LaborCategory", "Level of Effort (%)", "Vendor Name", "Hours"
    ]
    mock_execute = MagicMock(return_value=mock_result)

    # Mock DataFrame to include all columns
    mock_df = pd.DataFrame([{
        "Reporting Week": "2025-07-01",
        "ReportID": 1,
        "EmployeeID": 1,
        "WorkstreamID": 1,
        "WeekEnding": "2025-07-01",
        "LaborCategory": "Analyst",
        "Level of Effort (%)": "50%",
        "Vendor Name": "Vendor A",
        "Hours": 40,
    }])

    # Mock SQLAlchemy Table with required columns
    def table_factory(name, *args, **kwargs):
        table = MagicMock()
        table.c = MagicMock()
        for col in ["EmployeeID", "WorkstreamID", "AccomplishmentID"]:
            setattr(table.c, col, MagicMock())
        return table

    # Mock stmt with 8 columns
    mock_stmt = MagicMock()
    mock_stmt.columns.keys.return_value = mock_result.keys.return_value

    with patch("sqlalchemy.engine.base.Connection.execute", mock_execute), \
         patch("pandas.read_sql", MagicMock(return_value=mock_df)), \
         patch("sqlalchemy.Table", side_effect=table_factory), \
         patch(f"pages.{page_file[:-3]}.stmt", mock_stmt, create=True):
        spec = importlib.util.spec_from_file_location("page_module", file_path)
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
        except Exception as e:
            pytest.fail(f"Failed to import {page_file}: {e}")
