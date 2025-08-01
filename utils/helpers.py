import pandas as pd
import re
from datetime import date, timedelta, datetime
import hashlib
from sqlalchemy.sql import text
from utils.db import get_data, insert_row, update_row

# -----------------------------
# Constants
# -----------------------------
DEFAULT_ENTERED_BY = "system"

# -----------------------------
# Utility Functions
# -----------------------------

def get_most_recent_monday():
    """Returns the most recent Monday from today's date."""
    today = date.today()
    return today - timedelta(days=today.weekday())

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

# -----------------------------
# Core Helpers
# -----------------------------

def get_or_create_employee(conn=None, contractor_name=None, vendor=None, laborcategory=None, entered_by=DEFAULT_ENTERED_BY):
    """
    Retrieves or creates an employee with auditing fields.
    """
    contractor_norm = normalize_text(contractor_name or "")
    if not contractor_norm:
        return None

    vendor_norm = normalize_text(vendor or "Unknown Vendor")
    labor_norm = normalize_text(laborcategory or "Unknown LCAT")
    uniquekey = generate_employee_key(contractor_norm, vendor_norm)

    if conn:
        existing = conn.execute(
            text("SELECT EmployeeID FROM Employees WHERE UniqueKey = :key"),
            {"key": uniquekey}
        ).mappings().fetchone()
        if existing:
            return int(existing["EmployeeID"])

        result = conn.execute(
            text("""INSERT INTO Employees (Name, VendorName, LaborCategory, UniqueKey, CreatedAt, EnteredBy)
                    OUTPUT INSERTED.EmployeeID
                    VALUES (:name, :vendor, :lcat, :key, :created, :entered)"""),
            {
                "name": contractor_norm,
                "vendor": vendor_norm,
                "lcat": labor_norm,
                "key": uniquekey,
                "created": datetime.utcnow(),
                "entered": entered_by
            }
        )
        employee_id = result.scalar_one()
        conn.execute(
            text("UPDATE Employees SET PublicID = :pid WHERE EmployeeID = :eid"),
            {"pid": generate_public_id(contractor_norm, employee_id), "eid": employee_id}
        )
        return employee_id

    existing = get_data("Employees")
    match = existing[existing["UniqueKey"] == uniquekey]
    if not match.empty:
        return int(match.iloc[0]["EmployeeID"])

    employee_id = insert_row("Employees", {
        "Name": contractor_norm,
        "VendorName": vendor_norm,
        "LaborCategory": labor_norm,
        "UniqueKey": uniquekey,
        "CreatedAt": datetime.utcnow(),
        "EnteredBy": entered_by
    })
    update_row("Employees", employee_id, {
        "PublicID": generate_public_id(contractor_norm, employee_id)
    })
    return employee_id

def get_or_create_workstream(conn=None, workstream_name=None, entered_by=DEFAULT_ENTERED_BY):
    """
    Retrieves or creates a workstream with auditing.
    """
    workstream_norm = normalize_text(workstream_name or "")
    if not workstream_norm:
        return None

    if conn:
        existing_id = conn.execute(
            text("SELECT WorkstreamID FROM Workstreams WHERE LOWER(Name) = :name"),
            {"name": workstream_norm.lower()}
        ).scalar_one_or_none()
        if existing_id:
            return int(existing_id)

        new_id = conn.execute(
            text("""INSERT INTO Workstreams (Name, CreatedAt, EnteredBy)
                    OUTPUT INSERTED.WorkstreamID
                    VALUES (:name, :created, :entered)"""),
            {
                "name": workstream_norm,
                "created": datetime.utcnow(),
                "entered": entered_by
            }
        ).scalar_one()
        return int(new_id)

    existing = get_data("Workstreams")
    match = existing[existing["Name"].str.lower() == workstream_norm.lower()]
    if not match.empty:
        return int(match.iloc[0]["WorkstreamID"])

    return insert_row("Workstreams", {
        "Name": workstream_norm,
        "CreatedAt": datetime.utcnow(),
        "EnteredBy": entered_by
    })

# -----------------------------
# Insert Helpers
# -----------------------------

def insert_weekly_report(data: dict, entered_by=DEFAULT_ENTERED_BY):
    """Insert a Weekly Report with auditing."""
    return insert_row("WeeklyReports", {
        **data,
        "CreatedAt": datetime.utcnow(),
        "EnteredBy": entered_by
    })

def insert_accomplishment(data: dict, entered_by=DEFAULT_ENTERED_BY):
    """Insert an Accomplishment with auditing."""
    return insert_row("Accomplishments", {
        **data,
        "CreatedAt": datetime.utcnow(),
        "EnteredBy": entered_by
    })

def insert_hours_tracking(data: dict, entered_by=DEFAULT_ENTERED_BY):
    """Insert Hours Tracking with auditing."""
    return insert_row("HoursTracking", {
        **data,
        "CreatedAt": datetime.utcnow(),
        "EnteredBy": entered_by
    })
