import streamlit as st
import os
import pandas as pd
from sqlalchemy import create_engine, MetaData
from sqlalchemy.exc import OperationalError, InterfaceError, DBAPIError
import urllib
import time
from functools import wraps

_engine = None
_metadata = None
_tables = {}

# -------------- Retry Decorator -------------- #
def with_reconnect(func):
    """Decorator to retry DB operations and rebuild engine if needed."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        global _engine
        retries = 3
        delay = 2
        for attempt in range(retries):
            try:
                return func(*args, **kwargs)
            except (OperationalError, InterfaceError, DBAPIError):
                # Drop engine and retry
                _engine = None
                time.sleep(delay)
                delay *= 2
        raise RuntimeError("Database connection failed after retries")
    return wrapper


@st.cache_resource
def get_engine():
    """Create and cache SQLAlchemy engine for Azure SQL or SQLite fallback during tests."""
    global _engine
    if _engine is not None:
        return _engine

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


@st.cache_resource
@with_reconnect
def get_metadata():
    """Reflect and cache database metadata."""
    meta = MetaData()
    meta.reflect(
        bind=get_engine(),
        schema="dbo",
        only=["Employees", "Workstreams", "WeeklyReports", "Accomplishments", "HoursTracking"]
    )
    return meta


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

# Allow DB to be idle and auto-pause after 15 minutes
@st.cache_data(ttl=900)   # 8 * 3600 (8 hours)
@with_reconnect
def load_all_data():
    """Mass load all tables into cached DataFrames (shared cache)."""
    engine = get_engine()
    data = {}
    tables = ["Employees", "Workstreams", "WeeklyReports", "Accomplishments", "HoursTracking"]

    with engine.connect() as conn:
        for table in tables:
            data[table] = pd.read_sql(f"SELECT * FROM {table}", conn)

    return data


@st.cache_data(ttl=600)  # NEW: Single-table loader
@with_reconnect
def load_table(table_name: str):
    """Load only one table to avoid waking up DB unnecessarily."""
    engine = get_engine()
    with engine.connect() as conn:
        return pd.read_sql(f"SELECT * FROM {table_name}", conn)
        

def get_session_data():
    """Load data for this session only (no extra DB calls if shared cache is fresh)."""
    if "session_data" not in st.session_state:
        st.session_state["session_data"] = load_all_data()
    return st.session_state["session_data"]


def get_data(table_name: str) -> pd.DataFrame:
    """Access session-cached DataFrame for a specific table."""
    data = get_session_data()
    if table_name not in data:
        raise KeyError(f"Data for table '{table_name}' not found.")
    return data[table_name]


@with_reconnect
def insert_row(table_name: str, row_data: dict):
    """Insert data (short-lived connection) and refresh caches."""
    engine = get_engine()
    df = pd.DataFrame([row_data])
    with engine.begin() as conn:
        df.to_sql(table_name, conn, if_exists="append", index=False)

    # Clear both caches
    load_all_data.clear()
    if "session_data" in st.session_state:
        del st.session_state["session_data"]
