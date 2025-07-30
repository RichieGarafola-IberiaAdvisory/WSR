import pytest
import importlib.util
from pathlib import Path

PAGES_DIR = Path(__file__).parent.parent / "pages"
PAGE_FILES = [
    "01_Form_Submission.py",
    "02_Management_Dashboard.py",
    "03_HR_KPIs.py",
    "04_Accomplishments_Dashboard.py",
]

@pytest.mark.parametrize("page_file", PAGE_FILES)
def test_page_imports(page_file):
    """Smoke test: ensure each Streamlit page loads without errors."""
    file_path = PAGES_DIR / page_file
    spec = importlib.util.spec_from_file_location("page_module", file_path)
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as e:
        pytest.fail(f"Failed to import {page_file}: {e}")
