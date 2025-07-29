import os
from sqlalchemy import create_engine, MetaData
from dotenv import load_dotenv

# Safe import for Streamlit
try:
    import streamlit as st
    STREAMLIT_AVAILABLE = True
except ImportError:
    STREAMLIT_AVAILABLE = False

# Load variables from .env
load_dotenv()

# Use Streamlit secrets if available, otherwise fallback to .env
DATABASE_URL = None
if STREAMLIT_AVAILABLE and "DATABASE_URL" in st.secrets:
    DATABASE_URL = st.secrets["DATABASE_URL"]
else:
    DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL not set in environment variables or Streamlit secrets.")

# Ensure we're using pymssql (avoids ODBC driver issues on Streamlit Cloud)
if DATABASE_URL.startswith("mssql+pyodbc"):
    # Convert to pymssql format automatically
    DATABASE_URL = DATABASE_URL.replace("mssql+pyodbc", "mssql+pymssql")

# Internal module-level cache
_engine = None
_metadata = None
_tables = {}

# Global table references (lazy-loaded after calling load_tables)
employees = None
workstreams = None
weekly_reports = None
accomplishments = None
hourstracking = None

def get_engine():
    """Return a cached SQLAlchemy engine."""
    global _engine
    if _engine is None:
        if not DATABASE_URL:
            raise RuntimeError("DATABASE_URL not set. Cannot create engine.")
        _engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
    return _engine

def get_metadata():
    """Reflect and cache database metadata"""
    global _metadata
    if _metadata is None:
        _metadata = MetaData()
        _metadata.reflect(bind=get_engine())
    return _metadata

def get_table(name):
    """Return a reflected table by name, cashed for reuse."""
    meta = get_metadata()
    if name not in meta.tables:
        raise KeyError(f"Table '{name}' not found in database.")
    if name not in _tables:
        _tables[name] = meta.tables[name]
    return _tables[name]

def load_tables():
    """Call this after environment is confirmed set to initialize global table variables."""
    global employees, workstreams, weekly_reports, accomplishments, hourstracking
    employees = get_table("employees")
    workstreams = get_table("workstreams")
    weekly_reports = get_table("weeklyreports")
    accomplishments = get_table("accomplishments")
    hourstracking = get_table("hourstracking")

def db_healthcheck():
    """Simple connectivity check."""
    try:
        with get_engine().connect() as conn:
            conn.execute("SELECT 1")
        return True
    except Exception as e:
        print("Database health check failed:", e)
        return False

