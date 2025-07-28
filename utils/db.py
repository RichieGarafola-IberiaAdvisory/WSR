# This module provides a shared SQLAlchemy engine and lazy-loaded table references.
# Every page can simply:
# from utils.db import engine, employees, workstreams, weekly_reports, accomplishments, hours tracking
# Avoids repeating schema reflection and config.

import os
from sqlalchemy import create_engine, MetaData
from dotenv import load_dotenv

# Load variables from .env
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL not set in .env file.")
    
    
##########################
# PostGreSQL local option
##########################
# # Create engine and reflect schema metadata
# engine = create_engine(DATABASE_URL, echo=False)
# metadata = MetaData()
# metadata.reflect(bind=engine)


# Globals for lazy init
_engine = None
_metadata = None
_tables = {}

def get_engine():
    """Return a cached SQLAlchemy engine."""
    global _engine
    if _engine is None:
        _engine = create_engine(
            DATABASE_URL,
            echo=False,
            fast_executemany=True,
            pool_pre_ping=True
        )
    return _engine


def get_metadata():
    """Reflect and cache database metadata."""
    global _metadata
    if _metadata is None:
        _metadata = MetaData()
        _metadata.reflect(bind=get_engine())
    return _metadata

def get_table(name):
    """Return a reflected table by name, cached for reuse."""
    meta = get_metadata()
    name = name.lower()  # normalize
    for table_name, table_obj in meta.tables.items():
        if table_name.lower() == name:
            return table_obj
    raise KeyError(f"Table '{name}' not found in database.")


# -----------------------------
# Lazy table references
# -----------------------------
# These will only query metadata on first access
metadata = get_metadata()

employees = get_table("Employees")
workstreams = get_table("Workstreams")
weekly_reports = get_table("WeeklyReports")
accomplishments = get_table("Accomplishments")
hourstracking = get_table("HoursTracking")


def db_healthcheck():
    """Simple connectivity check."""
    try:
        with get_engine().connect() as conn:
            conn.execute("SELECT 1")
        return True
    except Exception as e:
        print("Database health check failed:", e)
        return False