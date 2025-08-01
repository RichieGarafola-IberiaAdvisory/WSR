import pandas as pd
import re
from datetime import date, timedelta
import hashlib
from sqlalchemy.sql import text
from utils.db import get_data, insert_row


def get_most_recent_monday():
    """Returns the most recent Monday from today's date."""
    today = date.today()
    return today - timedelta(days=today.weekday())


def get_or_create_employee(conn=None, contractor_name=None, vendor=None, laborcategory=None):
    """
    Retrieves an existing employee from the Employees table or inserts a new one if not found.
    Supports optional conn parameter for testing.
    """
    contractor_name = (contractor_name or "").strip()
    if not contractor_name:
        return None

    vendor = vendor or "Unknown Vendor"
    laborcategory = laborcategory or "Unknown LCAT"
    uniquekey = generate_employee_key(contractor_name, vendor)

    if conn:  # Test mode
        existing = conn.execute(
            text("SELECT EmployeeID FROM Employees WHERE UniqueKey = :key"),
            {"key": uniquekey}
        ).mappings().fetchone()
        if existing:
            return int(existing["EmployeeID"])

        # Insert new employee
        result = conn.execute(
            text("INSERT INTO Employees (Name, VendorName, LaborCategory, UniqueKey) "
                 "OUTPUT INSERTED.EmployeeID "
                 "VALUES (:name, :vendor, :lcat, :key)"),
            {"name": contractor_name, "vendor": vendor, "lcat": laborcategory, "key": uniquekey}
        )
        employee_id = result.scalar_one()
        conn.execute(
            text("UPDATE Employees SET PublicID = :pid WHERE EmployeeID = :eid"),
            {"pid": generate_public_id(contractor_name, employee_id), "eid": employee_id}
        )
        return employee_id
    else:  # Production
        existing = get_data("Employees")
        match = existing[existing["UniqueKey"] == uniquekey]
        if not match.empty:
            return int(match.iloc[0]["EmployeeID"])

        employee_id = insert_row("Employees", {
            "Name": contractor_name,
            "VendorName": vendor,
            "LaborCategory": laborcategory,
            "UniqueKey": uniquekey
        })
        publicid = generate_public_id(contractor_name, employee_id)
        insert_row("Employees", {
            "EmployeeID": employee_id,
            "PublicID": publicid
        })
        return employee_id



def get_or_create_workstream(conn=None, workstream_name=None):
    """
    Retrieves an existing workstream or inserts a new one if not found.
    Supports optional conn parameter for testing.
    """
    workstream_name = (workstream_name or "").strip()
    if not workstream_name:
        return None

    normalized_name = normalize_text(workstream_name)

    if conn:  # Test mode or direct DB connection
        # Check if the workstream already exists
        existing_id = conn.execute(
            text("SELECT WorkstreamID FROM Workstreams WHERE LOWER(Name) = :name"),
            {"name": normalized_name.lower()}
        ).scalar_one_or_none()

        if existing_id is not None:
            return int(existing_id)

        # Insert a new workstream and return its ID
        new_id = conn.execute(
            text("INSERT INTO Workstreams (Name) VALUES (:name) RETURNING WorkstreamID"),
            {"name": normalized_name}
        ).scalar_one()
        return int(new_id)

    # Production mode (no direct connection provided)
    existing = get_data("Workstreams")
    match = existing[existing["Name"].str.lower() == normalized_name.lower()]
    if not match.empty:
        return int(match.iloc[0]["WorkstreamID"])

    return insert_row("Workstreams", {"Name": normalized_name})


def normalize_text(value: str) -> str:
    """Trims, collapses spaces, and converts to title case."""
    if not isinstance(value, str):
        return ""
    return re.sub(r"\s+", " ", value.strip()).title()

def clean_dataframe_dates_hours(df, date_cols=None, numeric_cols=None):
    """Clean DataFrame date and numeric columns."""
    df = df.copy()
    
    if date_cols:
        for col in date_cols:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")
    
    if numeric_cols:
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
    
    return df

def generate_employee_key(name: str, vendor: str) -> str:
    """Creates a SHA-256 hash key to uniquely identify an employee."""
    base = f'{normalize_text(name)}|{normalize_text(vendor)}'
    return hashlib.sha256(base.encode()).hexdigest()


def generate_public_id(name: str, numeric_id: int) -> str:
    """Generates a public ID in the format LAST-FIRST-###."""
    parts = normalize_text(name).split()
    base = f"{parts[-1]}-{parts[0]}" if len(parts) >= 2 else parts[0]
    return f"{base.upper()}-{numeric_id:03d}"
