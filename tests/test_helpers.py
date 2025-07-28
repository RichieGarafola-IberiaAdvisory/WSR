import pytest
from unittest.mock import MagicMock
from utils import helpers
import pandas as pd

# -------------------------------
# normalize_text
# -------------------------------
def test_normalize_text_basic():
    assert helpers.normalize_text(" john   doe ") == "John Doe"
    assert helpers.normalize_text("") == ""
    assert helpers.normalize_text(None) == ""
    assert helpers.normalize_text("  MULTI   line\nName  ") == "Multi Line Name"


# -------------------------------
# generate_employee_key
# -------------------------------
def test_generate_employee_key_is_deterministic():
    k1 = helpers.generate_employee_key("John Doe", "Vendor A")
    k2 = helpers.generate_employee_key(" John  Doe ", "  Vendor A ")
    assert k1 == k2
    assert isinstance(k1, str)
    assert len(k1) == 64  # SHA-256 hex length


# -------------------------------
# generate_public_id
# -------------------------------
def test_generate_public_id_two_part_name():
    pubid = helpers.generate_public_id("John Doe", 42)
    assert pubid == "DOE-JOHN-042"

def test_generate_public_id_one_part_name():
    pubid = helpers.generate_public_id("Plato", 7)
    assert pubid == "PLATO-007"


# -------------------------------
# clean_dataframe_dates_hours
# -------------------------------
def test_clean_dataframe_dates_hours():
    df = pd.DataFrame({
        "d1": ["2024-01-01", "bad date", None],
        "n1": ["10", "bad", None]
    })
    cleaned = helpers.clean_dataframe_dates_hours(df, date_cols=["d1"], numeric_cols=["n1"])
    assert pd.api.types.is_datetime64_any_dtype(cleaned["d1"])
    assert pd.api.types.is_float_dtype(cleaned["n1"])
    assert cleaned["n1"].iloc[1] == 0  # bad value becomes 0


# -------------------------------
# get_or_create_employee
# -------------------------------
def test_get_or_create_employee_existing():
    mock_conn = MagicMock()
    mock_conn.execute.return_value.mappings.return_value.fetchone.return_value = {
        "EmployeeID": 1,
        "VendorName": "",
        "LaborCategory": "Unknown LCAT"
    }

    result = helpers.get_or_create_employee(mock_conn, "John Doe", "VendorX", "Manager")

    assert result == 1
    assert mock_conn.execute.call_count >= 2  # select + update(s)

def test_get_or_create_employee_insert_new():
    mock_conn = MagicMock()
    mock_conn.execute.side_effect = [
        MagicMock(mappings=lambda: MagicMock(fetchone=lambda: None)),  # not found
        MagicMock(scalar_one=lambda: 5),  # insert returns ID
        None  # update publicid
    ]

    result = helpers.get_or_create_employee(mock_conn, "Jane Smith", "VendorY", "Engineer")
    assert result == 5

def test_get_or_create_employee_blank_name_returns_none():
    mock_conn = MagicMock()
    result = helpers.get_or_create_employee(mock_conn, "   ")
    assert result is None


# -------------------------------
# get_or_create_workstream
# -------------------------------
def test_get_or_create_workstream_existing():
    mock_conn = MagicMock()
    mock_conn.execute.return_value.scalar_one_or_none.return_value = 3    
    result = helpers.get_or_create_workstream(mock_conn, "Data Ops")    
    assert result == 3


def test_get_or_create_workstream_insert_new():
    mock_conn = MagicMock()
    mock_conn.execute.side_effect = [
        MagicMock(scalar_one_or_none=lambda: None),  # SELECT returns no existing workstream
        MagicMock(scalar_one=lambda: 7)              # INSERT returns ID 7
    ]

    result = helpers.get_or_create_workstream(mock_conn, "Innovation Lab")

    assert result == 7
