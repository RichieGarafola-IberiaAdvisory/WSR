import pandas as pd
import re
from datetime import date, timedelta
import hashlib
from utils.db import get_data, insert_row


def get_most_recent_monday():
    """Returns the most recent Monday from today's date."""
    today = date.today()
    return today - timedelta(days=today.weekday())


def get_or_create_employee(contractor_name, vendor=None, laborcategory=None):
    """
    Retrieves an existing employee from the Employees table or inserts a new one if not found.
    Uses a deterministic SHA-256 UniqueKey to avoid duplicates.
    """
    contractor_name = contractor_name.strip()
    if not contractor_name:
        return None

    vendor = vendor or "Unknown Vendor"
    laborcategory = laborcategory or "Unknown LCAT"
    uniquekey = generate_employee_key(contractor_name, vendor)

    existing = get_data("Employees")
    match = existing[existing["UniqueKey"] == uniquekey]

    if not match.empty:
        return int(match.iloc[0]["EmployeeID"])

    # Insert new employee
    employee_id = insert_row("Employees", {
        "Name": contractor_name,
        "VendorName": vendor,
        "LaborCategory": laborcategory,
        "UniqueKey": uniquekey
    })

    # Generate and store public ID
    publicid = generate_public_id(contractor_name, employee_id)
    insert_row("Employees", {
        "EmployeeID": employee_id,
        "PublicID": publicid
    })

    return employee_id


def get_or_create_workstream(workstream_name):
    """
    Retrieves an existing workstream or inserts a new one if not found.
    Performs a case-insensitive match to prevent duplicates.
    """
    workstream_name = workstream_name.strip()
    if not workstream_name:
        return None

    normalized_name = normalize_text(workstream_name)

    existing = get_data("Workstreams")
    match = existing[existing["Name"].str.lower() == normalized_name.lower()]

    if not match.empty:
        return int(match.iloc[0]["WorkstreamID"])

    return insert_row("Workstreams", {"Name": normalized_name})


def clean_dataframe_dates_hours(df, date_cols, numeric_cols):
    """Cleans and coerces date and numeric columns for database compatibility."""
    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    return df


def normalize_text(value: str) -> str:
    """Trims, collapses spaces, and converts to title case."""
    if not isinstance(value, str):
        return ""
    return re.sub(r"\s+", " ", value.strip()).title()


def generate_employee_key(name: str, vendor: str) -> str:
    """Creates a SHA-256 hash key to uniquely identify an employee."""
    base = f'{normalize_text(name)}|{normalize_text(vendor)}'
    return hashlib.sha256(base.encode()).hexdigest()


def generate_public_id(name: str, numeric_id: int) -> str:
    """Generates a public ID in the format LAST-FIRST-###."""
    parts = normalize_text(name).split()
    base = f"{parts[-1]}-{parts[0]}" if len(parts) >= 2 else parts[0]
    return f"{base.upper()}-{numeric_id:03d}"
