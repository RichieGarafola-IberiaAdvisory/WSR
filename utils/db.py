import os
from sqlalchemy import create_engine, MetaData
from dotenv import load_dotenv

# Load variables from .env
load_dotenv()

# Load DATABASE_URL but don't raise an error yet
DATABASE_URL = os.getenv("DATABASE_URL")

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
        if not DATABASE_URL:
            raise RuntimeError("DATABASE_URL not set. Cannot create engine.")
        _engine = create_engine(DATABASE_URL, echo=False)
    return _engine

def get_metadata():
    global _metadata
    if _metadata is None:
        _metadata = MetaData()
        _metadata.reflect(bind=get_engine())
    return _metadata

def get_table(name):
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
