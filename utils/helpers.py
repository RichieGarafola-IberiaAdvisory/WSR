import pandas as pd
import re
from datetime import date, timedelta
from sqlalchemy import select, insert, func
import hashlib

from utils.db import employees, workstreams

def get_most_recent_monday():
    """
    Returns the most recent Monday from today's date.

    Returns:
        datetime.date: Date of the most recent Monday.
    """
    today = date.today()
    return today - timedelta(days=today.weekday())


def get_or_create_employee(conn, contractor_name, vendor=None, laborcategory=None):
    """
    Retrieves an existing employee from the Employees table or inserts a new one if not found.

    - Checks for an existing employee using a deterministic UniqueKey 
      (SHA-256 hash of contractor name + vendor).
    - If found, returns the existing EmployeeID (avoids duplicate inserts).
    - If not found, inserts a new employee, generates a public ID, and returns the new EmployeeID.
    - Ensures vendor and labor category values are stored with defaults if missing.

    Args:
        conn (Connection): Active SQLAlchemy database connection.
        contractor_name (str): Full name of the employee (required).
        vendor (str, optional): Vendor/company name. Defaults to "Unknown Vendor".
        laborcategory (str, optional): Labor category or title. Defaults to "Unknown LCAT".

    Returns:
        int: The primary key EmployeeID for the existing or newly created employee.
              Returns None if contractor_name is empty.
    """
    from utils.db import employees  # Local import to avoid NoneType errors in tests
    
    contractor_name = contractor_name.strip()
    if not contractor_name:
        return None

    vendor = vendor or "Unknown Vendor"
    laborcategory = laborcategory or "Unknown LCAT"
    uniquekey = generate_employee_key(contractor_name, vendor)

    # Look for existing employee
    emp = conn.execute(
        select(employees.c.EmployeeID)
        .where(employees.c.UniqueKey == uniquekey)
    ).mappings().fetchone()

    if emp:
        return emp["EmployeeID"]  # Use existing EmployeeID

    # Insert only if not found
    result = conn.execute(
        insert(employees).values(
            Name=contractor_name,
            VendorName=vendor,
            LaborCategory=laborcategory,
            UniqueKey=uniquekey
        ).returning(employees.c.EmployeeID)
    )
    employeeid = result.scalar_one()

    # Generate public ID
    publicid = generate_public_id(contractor_name, employeeid)
    conn.execute(
        employees.update()
        .where(employees.c.EmployeeID == employeeid)
        .values(PublicID=publicid)
    )

    return employeeid


def get_or_create_workstream(conn, workstream_name):
    """
    Retrieves an existing workstream from the Workstreams table or inserts a new one if not found.

    - Performs a case-insensitive search for the given workstream name.
    - Normalizes the name (trims whitespace, collapses spaces, and title-cases).
    - If an existing workstream with the same normalized name is found, 
      its WorkstreamID is returned.
    - If not found, a new workstream record is inserted and its WorkstreamID returned.
    - Prevents duplicate workstream creation due to inconsistent casing or spacing.

    Args:
        conn (Connection): Active SQLAlchemy database connection.
        workstream_name (str): Name of the workstream (required).

    Returns:
        int: The primary key WorkstreamID for the existing or newly created workstream.
             Returns None if workstream_name is empty.
    """
    from utils.db import workstreams  # Local import to avoid NoneType errors in tests
    
    workstream_name = workstream_name.strip()
    if not workstream_name:
        return None

    normalized_name = normalize_text(workstream_name)

    # Check if workstream already exists (case-insensitive)
    ws = conn.execute(
        select(workstreams.c.WorkstreamID).where(
            func.lower(workstreams.c.Name) == func.lower(normalized_name)
        )
    ).scalar_one_or_none()

    if ws is not None:
        return ws  # Existing workstream found

    # Insert new workstream
    result = conn.execute(
        insert(workstreams).values(
            Name=normalized_name
        ).returning(workstreams.c.WorkstreamID)
    )

    return result.scalar_one()




def clean_dataframe_dates_hours(df, date_cols, numeric_cols):
    """
    Cleans and coerces date and numeric columns in a DataFrame to ensure
    compatibilitiy with database schemas (especially PostgreSQL).
    
    Parameters:
        df (pd.DataFrame): The input Dataframe to clean
        date_cols (list): List of column names to convert to datetime
        numeric_cols (list): List of column names to convert to numeric (float).
        
    Returns:
        pd.DataFrame: The cleaned Dataframe with proper types.
    """
    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
            
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
            
    return df


def normalize_text(value: str) -> str:
    """
    Normalizes a string by trimming whitespace, collapsing internal spaces,
    and converting to title case.

    Args:
        value (str): Input string.

    Returns:
        str: Cleaned and formatted string.
    """
    
    if not isinstance(value, str):
        return ""
    return re.sub(r"\s+", " ", value.strip()).title()

def generate_employee_key(name: str, vendor: str) -> str:
    """
    Creates a deterministic SHA-256 hash key from employee name and vendor.
    Used to uniquely identify personnel.

    Args:
        name (str): Full name.
        vendor (str): Vendor name.

    Returns:
        str: Hexadecimal SHA-256 hash string.
    """
    
    base = f'{normalize_text(name)}|{normalize_text(vendor)}'
    return hashlib.sha256(base.encode()).hexdigest()

def generate_public_id(name: str, numeric_id: int) -> str:
    """
    Generates a readable public ID in the format LAST-FIRST-### based on name and ID.

    Args:
        name (str): Full name.
        numeric_id (int): Employee ID.

    Returns:
        str: Public identifier string.
    """
    parts = normalize_text(name).split()
    if len(parts) >= 2:
        base = f"{parts[-1]}-{parts[0]}"  # last - first
    else:
        base = parts[0]
    return f"{base.upper()}-{numeric_id:03d}"