import pandas as pd
import re
from datetime import date, timedelta
from sqlalchemy import select, insert, func
import hashlib

from utils.db import employees, workstreams, hourstracking, employees

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
    Retrieves an existing employee by their unique (name + vendor) key,
    or inserts a new one if not found. Ensures vendor and labor category are backfilled,
    and assigns a public ID if newly inserted.

    Args:
        conn (Connection): SQLAlchemy database connection.
        contractor_name (str): Full name of the employee.
        vendor (str, optional): Vendor/company name. Defaults to "Unknown Vendor".
        laborcategory (str, optional): Job title or labor category. Defaults to "Unknown LCAT".

    Returns:
        int: The employee ID (primary key).
    """
        
    contractor_name = contractor_name.strip()
    if not contractor_name:
        return None

    vendor = vendor or "Unknown Vendor"
    laborcategory = laborcategory or "Unknown LCAT"
    uniquekey = generate_employee_key(contractor_name, vendor)

    # Look up by unique hash
    emp = conn.execute(
        select(employees).where(employees.c.uniquekey == uniquekey)
    ).mappings().fetchone()

    if emp:
        employeeid = emp["employeeid"]

        # Backfill if needed
        if not emp["vendorname"] or emp["vendorname"].strip().lower() == "unknown vendor":
            conn.execute(
                employees.update()
                .where(employees.c.employeeid == employeeid)
                .values(vendorname=vendor)
            )
        if not emp["laborcategory"] or emp["laborcategory"].strip().lower() == "unknown lcat":
            conn.execute(
                employees.update()
                .where(employees.c.employeeid == employeeid)
                .values(laborcategory=laborcategory)
            )

    else:
        # Insert new employee
        result = conn.execute(
            insert(employees).values(
                name=contractor_name,
                vendorname=vendor,
                laborcategory=laborcategory,
                uniquekey=uniquekey
            ).returning(employees.c.employeeid)
        )
        employeeid = result.scalar_one()

        # Generate and assign public ID
        publicid = generate_public_id(contractor_name, employeeid)
        conn.execute(
            employees.update()
            .where(employees.c.employeeid == employeeid)
            .values(publicid=publicid)
        )

    return employeeid


def get_or_create_workstream(conn, workstream_name):
    """
    Retrieves an existing workstream by name (case-insensitive),
    or inserts it if not found. Normalizes name formatting.

    Args:
        conn (Connection): SQLAlchemy database connection.
        workstream_name (str): Name of the workstream.

    Returns:
        int: The workstream ID.
    """
        
    workstream_name = workstream_name.strip()
    if not workstream_name:
        return None

    normalized_name = normalize_text(workstream_name)

    ws = conn.execute(
        select(workstreams.c.workstreamid).where(
            func.lower(workstreams.c.name) == normalized_name.lower()
        )
    ).scalar_one_or_none()

    if ws is not None:
        return ws

    result = conn.execute(
        insert(workstreams).values(name=normalized_name).returning(workstreams.c.workstreamid)
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

