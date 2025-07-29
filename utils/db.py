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
    
    employees = employees or get_table("Employees")
    workstreams = workstreams or get_table("Workstreams")
    weekly_reports = weekly_reports or get_table("WeeklyReports")
    accomplishments = accomplishments or get_table("Accomplishments")
    hourstracking = hourstracking or get_table("HoursTracking")
