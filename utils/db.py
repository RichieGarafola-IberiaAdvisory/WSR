import streamlit as st
import os
from sqlalchemy import create_engine, MetaData
import urllib

# Internal cache
_engine = None
_metadata = None
_tables = {}

# Lazy-loaded table references
employees = None
workstreams = None
weekly_reports = None
accomplishments = None
hourstracking = None


def get_engine():
    """Create and cache SQLAlchemy engine for Azure SQL."""
    global _engine
    if _engine is None:
        connection_string = st.secrets.get("DATABASE_URL") or os.getenv("DATABASE_URL")
        if not connection_string:
            raise RuntimeError("DATABASE_URL not found")

        # Try Driver 18 first, fallback to 17
        if "ODBC Driver 18" in connection_string:
            try:
                params = urllib.parse.quote_plus(connection_string)
                _engine = create_engine(f"mssql+pyodbc:///?odbc_connect={params}")
            except Exception:
                # Fallback to Driver 17
                connection_string = connection_string.replace("ODBC Driver 18", "ODBC Driver 17")
                params = urllib.parse.quote_plus(connection_string)
                _engine = create_engine(
                    f"mssql+pyodbc:///?odbc_connect={params}",
                    pool_size=5,
                    max_overflow=10,
                    pool_recycle=1800,  # recycle every 30 min
                    pool_pre_ping=True  # checks connections before using
                )
        else:
            params = urllib.parse.quote_plus(connection_string)
            _engine = create_engine(f"mssql+pyodbc:///?odbc_connect={params}")

    return _engine

def get_metadata():
    """Reflect and cache database metadata."""
    global _metadata
    if _metadata is None:
        _metadata = MetaData()
        _metadata.reflect(
            bind=get_engine(),
            schema="dbo",
            only=[
                "Employees",
                "Workstreams",
                "WeeklyReports",
                "Accomplishments",
                "HoursTracking"
            ]
        )
    return _metadata

def get_table(name):
    """Retrieve a table object by name with caching."""
    meta = get_metadata()
    name_lower = name.lower()

    # Cache Check
    if name_lower in _tables:
        return _tables[name_lower]

    # Match ignoring schema
    for table_name, table_obj in meta.tables.items():
        if table_name.split('.')[-1].lower() == name_lower:
            _tables[name_lower] = table_obj
            return table_obj
            
    # Debug output if table not found
    all_tables = list(meta.tables.keys())
    raise KeyError(f"❌ Table '{name}' not found. Found tables: {all_tables}")


def load_tables():
    """Lazy-load global table references."""
    global employees, workstreams, weekly_reports, accomplishments, hourstracking
    
if employees is None:
    employees = get_table("Employees")
if workstreams is None:
    workstreams = get_table("Workstreams")
if weekly_reports is None:
    weekly_reports = get_table("WeeklyReports")
if accomplishments is None:
    accomplishments = get_table("Accomplishments")
if hourstracking is None:
    hourstracking = get_table("HoursTracking")

