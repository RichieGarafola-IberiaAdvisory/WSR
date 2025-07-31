import pytest
import pandas as pd
from unittest.mock import patch, MagicMock
import importlib
from pathlib import Path

PAGES_DIR = Path("pages")
PAGE_FILES = [f.name for f in PAGES_DIR.glob("*.py") if not f.name.startswith("__")]

@pytest.mark.parametrize("page_file", PAGE_FILES)
def test_page_imports(page_file):
    """
    Smoke test: Ensure each Streamlit page loads without DB/data errors.
    Automatically adapts to each page's required SQL columns.
    """
    module_name = f"pages.{page_file[:-3]}"
    
    # Dynamically import the page module
    page_module = importlib.import_module(module_name)

    # Detect stmt columns if available
    stmt_columns = getattr(getattr(page_module, "stmt", None), "columns", None)
    if stmt_columns is not None:
        stmt_keys = list(stmt_columns.keys())
    else:
        # Fallback for pages without stmt
        stmt_keys = [
            "ReportID", "EmployeeID", "WorkstreamID",
            "WeekEnding", "LaborCategory", "Level of Effort (%)",
            "Vendor Name", "Hours"
        ]

    # Generate dummy DB row with same number of columns
    db_values = tuple(range(1, len(stmt_keys) + 1))

    # Mock fetch result
    mock_result = MagicMock()
    mock_result.fetchall.return_value = [db_values]
    mock_result.keys.return_value = stmt_keys
    mock_execute = MagicMock(return_value=mock_result)

    # Mock DataFrame
    mock_df = pd.DataFrame([dict(zip(stmt_keys, db_values))])

    # Mock SQLAlchemy Table
    def table_factory(name, *args, **kwargs):
        table = MagicMock()
        table.c = MagicMock()
        for col in ["EmployeeID", "WorkstreamID", "AccomplishmentID"]:
            setattr(table.c, col, MagicMock())
        return table

    # Mock stmt itself (matching dynamic columns)
    mock_stmt = MagicMock()
    mock_stmt.columns.keys.return_value = stmt_keys

    with patch("sqlalchemy.engine.base.Connection.execute", mock_execute), \
         patch("pandas.read_sql", MagicMock(return_value=mock_df)), \
         patch("sqlalchemy.Table", side_effect=table_factory), \
         patch(f"{module_name}.stmt", mock_stmt, create=True):
        importlib.reload(page_module)
