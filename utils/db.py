import streamlit as st
import os
import pandas as pd
from sqlalchemy import create_engine, MetaData, text
from sqlalchemy.exc import OperationalError, InterfaceError, DBAPIError
import urllib
import time
import threading
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

_engine_lock = threading.Lock()
@st.cache_resource
def get_engine():
    """Create and cache SQLAlchemy engine for Azure SQL or SQLite fallback during tests."""
    global _engine
    with _engine_lock:
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
        only=["Employees", "Workstreams", "WeeklyReports", "HoursTracking"]
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


# -------------------------------
# Expected Table Schemas (fallbacks)
# -------------------------------
TABLE_SCHEMAS = {
    "Employees": [
        "EmployeeID", "Name", "VendorName", "LaborCategory", 
        "UniqueKey", "PublicID", "CreatedAt", "EnteredBy"
    ],
    "Workstreams": [
        "WorkstreamID", "Name", "CreatedAt", "EnteredBy"
    ],
    "WeeklyReports": [
        "ReportID", "EmployeeID", "WorkstreamID", "WeekStartDate", 
        "DivisionCommand", "WorkProductTitle", "ContributionDescription", 
        "Status", "PlannedOrUnplanned", "DateCompleted", "DistinctNFR", 
        "DistinctCAP", "EffortPercentage", "ContractorName", "GovtTAName",
        "Accomplishment1", "Accomplishment2", "Accomplishment3",
        "Accomplishment4", "Accomplishment5",
        "CreatedAt", "EnteredBy"
    ],
    "HoursTracking": [
        "EntryID", "EmployeeID", "WorkstreamID", 
        "ReportingWeek", "HoursWorked", "LevelOfEffort", 
        "CreatedAt", "EnteredBy"
    ]
}

PRIMARY_KEYS = {
    "Employees": "EmployeeID",
    "Workstreams": "WorkstreamID",
    "WeeklyReports": "ReportID",
    "HoursTracking": "EntryID"
}

def update_row(table_name: str, row_id: int, data: dict):
    """    Updates a row in the specified table by its primary key."""
    pk = PRIMARY_KEYS.get(table_name, f"{table_name[:-1]}ID")
    with get_engine().begin() as conn:
        set_clause = ", ".join([f"{col} = :{col}" for col in data.keys()])
        query = text(f"UPDATE {table_name} SET {set_clause} WHERE {pk} = :id")
        conn.execute(query, {"id": row_id, **data})

def _empty_table(name: str) -> pd.DataFrame:
    """Return an empty DataFrame with the expected schema."""
    cols = TABLE_SCHEMAS.get(name, [])
    return pd.DataFrame(columns=cols)

@st.cache_data(ttl=300)
@with_reconnect
def load_all_data():
    """Mass load all tables or provide schema fallbacks."""
    engine = get_engine()
    data = {}
    tables = TABLE_SCHEMAS.keys()

    try:
        with engine.connect() as conn:
            for table in tables:
                df = pd.read_sql(f"SELECT * FROM {table}", conn)
                if df.empty:
                    df = _empty_table(table)
                data[table] = df
    except Exception:
        # Test or offline mode
        data = {table: _empty_table(table) for table in tables}

    return data

@st.cache_data(ttl=600)
@with_reconnect
def load_table(table_name: str):
    """Load single table or fallback schema."""
    engine = get_engine()
    try:
        with engine.connect() as conn:
            df = pd.read_sql(f"SELECT * FROM {table_name}", conn)
            if df.empty:
                return _empty_table(table_name)
            return df
    except Exception:
        return _empty_table(table_name)

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
    """Insert data (short-lived connection), return inserted ID if available, and refresh caches."""
    engine = get_engine()
    with engine.begin() as conn:
        cols = ", ".join(row_data.keys())
        vals = ", ".join([f":{k}" for k in row_data.keys()])
        # Dynamically fetch the primary key for OUTPUT
        id_col = PRIMARY_KEYS.get(table_name)

        if id_col:
            result = conn.execute(
                text(f"INSERT INTO {table_name} ({cols}) OUTPUT INSERTED.{id_col} VALUES ({vals})"),
                row_data
            )
            inserted_id = result.scalar_one()
        else:
            conn.execute(
                text(f"INSERT INTO {table_name} ({cols}) VALUES ({vals})"),
                row_data
            )
            inserted_id = None

    # Clear caches
    load_all_data.clear()
    if "session_data" in st.session_state:
        del st.session_state["session_data"]

    return inserted_id

