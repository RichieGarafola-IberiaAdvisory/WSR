import streamlit as st
import os
import pandas as pd
from sqlalchemy import create_engine, MetaData
import urllib

# Internal cache
_engine = None
_metadata = None
_tables = {}

# Cached DataFrame store
_cached_data = {}

def get_engine():
    """Create and cache SQLAlchemy engine for Azure SQL or SQLite fallback during tests."""
    global _engine
    if _engine is None:
        if os.getenv("PYTEST_CURRENT_TEST") or os.getenv("DATABASE_URL", "").startswith("sqlite"):
            _engine = create_engine("sqlite:///:memory:", future=True)
            return _engine

        connection_string = st.secrets.get("DATABASE_URL") or os.getenv("DATABASE_URL")
        if not connection_string:
            raise RuntimeError("DATABASE_URL not found")

        try:
            params = urllib.parse.quote_plus(connection_string)
            _engine = create_engine(
                f"mssql+pyodbc:///?odbc_connect={params}",
                pool_size=5,
                max_overflow=10,
                pool_recycle=1800,
                pool_pre_ping=True
            )
        except Exception:
            connection_string = connection_string.replace("ODBC Driver 18", "ODBC Driver 17")
            params = urllib.parse.quote_plus(connection_string)
            _engine = create_engine(
                f"mssql+pyodbc:///?odbc_connect={params}",
                pool_size=5,
                max_overflow=10,
                pool_recycle=1800,
                pool_pre_ping=True
            )
    return _engine


def get_metadata():
    """Reflect and cache database metadata."""
    global _metadata
    if _metadata is None:
        _metadata = MetaData()
        _metadata.reflect(
            bind=get_engine(),
            schema="dbo",
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
        if table_name.split('.')[-1].lower() == name_lower:
            _tables[name_lower] = table_obj
            return table_obj
            
    raise KeyError(f"Table '{name}' not found. Found tables: {list(meta.tables.keys())}")


@st.cache_data(ttl=8*3600)
def load_all_data():
    """Load all tables into cached DataFrames (1 query each, once per hour)."""
    engine = get_engine()
    data = {}
    
    tables = ["Employees", "Workstreams", "WeeklyReports", "Accomplishments", "HoursTracking"]
    
    with engine.connect() as conn:
        for table in tables:
            data[table] = pd.read_sql(f"SELECT * FROM {table}", conn)
    
    return data


def get_data(table_name: str) -> pd.DataFrame:
    """Access cached DataFrame for a specific table."""
    data = load_all_data()
    if table_name not in data:
        raise KeyError(f"Data for table '{table_name}' not found.")
    return data[table_name]


def insert_row(table_name: str, row_data: dict):
    """Insert data (write only, keeps connection short-lived)."""
    engine = get_engine()
    df = pd.DataFrame([row_data])
    with engine.begin() as conn:
        df.to_sql(table_name, conn, if_exists="append", index=False)
    
    # Clear cached data so next call refreshes
    load_all_data.clear()
