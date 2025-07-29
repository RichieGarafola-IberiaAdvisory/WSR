import os
from sqlalchemy import create_engine, MetaData
from dotenv import load_dotenv

# Load variables from .env
load_dotenv()

# Load DATABASE_URL but don't raise an error yet
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL not set in environment variables or Streamlit secrets.")

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
    global _engine
    if _engine is None:
        _engine = create_engine(
            DATABASE_URL,
            echo=False,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True
        )
    return _engine

def get_metadata():
    """Reflect and cache database metadata."""
    global _metadata
    if _metadata is None:
        _metadata = MetaData()
        _metadata.reflect(bind=get_engine(),
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
    """Lazy-load global table references only when called."""
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
    
# Automatically load tables on import    
load_tables()