import streamlit as st
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
    """Create and cache SQLAlchemy engine for MS SQL Server."""
    global _engine
    if _engine is None:
        connection_string = st.secrets["DATABASE_URL"]
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
            only=["Employees", "Workstreams", "WeeklyReports", "Accomplishments", "HoursTracking"]
        )
    return _metadata


def get_table(name):
    """Retrieve a table object by name with caching."""
    meta = get_metadata()
    name_lower = name.lower()
    if name_lower in _tables:
        return _tables[name_lower]
    
    for table_name, table_obj in meta.tables.items():
        if table_name.lower() == name_lower:
            _tables[name_lower] = table_obj
            return table_obj
    
    raise KeyError(f"Table '{name}' not found in database.")


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
