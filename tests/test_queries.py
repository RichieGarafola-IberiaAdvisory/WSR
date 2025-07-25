# tests/test_queries.py
from utils import queries
from sqlalchemy import text

def test_weekly_reports_query_compiles():
    try:
        q = text(queries.weekly_reports_with_employees)
        assert "SELECT" in str(q)
    except Exception as e:
        pytest.fail(f"Query did not compile: {e}")
