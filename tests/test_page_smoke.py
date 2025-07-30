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


PAGES_WITH_FUNCS = [
    ("01_Form_Submission.py", "submit_form"),  # only if you added it
    ("02_Management_Dashboard.py", "render_dashboard"),
    ("03_HR_KPIs.py", "render_kpis"),
    ("04_Accomplishments_Dashboard.py", "render_accomplishments"),
]

@pytest.mark.parametrize("page_file, func_name", PAGES_WITH_FUNCS)
def test_page_main_functions(page_file, func_name):
    """Ensure each page's main function exists and can be called."""
    file_path = PAGES_DIR / page_file
    spec = importlib.util.spec_from_file_location("page_module", file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    render_func = getattr(module, func_name, None)
    assert callable(render_func), f"{func_name} missing in {page_file}"
    
    # Call the function (should return True or not raise errors)
    result = render_func()
    assert result is True or result is None
