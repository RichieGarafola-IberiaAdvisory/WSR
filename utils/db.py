# Every page can simply from utils.db import engine, employees, workstreams, weekly_reports, accomplishments, hours tracking
# Avoids repeating schema reflection and config.

import os
from sqlalchemy import create_engine, MetaData
from dotenv import load_dotenv

# Load variables from .env
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL not set in .env file.")
    

# Create engine and reflect schema metadata
engine = create_engine(DATABASE_URL, echo=False)
metadata = MetaData()
metadata.reflect(bind=engine)

_engine = None
_metadata = None
_tables = {}

def get_engine():
    global _engine
    if _engine is None:
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


# Shortcut variables table references (lazy-loaded)
employees = get_table("employees")
workstreams = get_table("workstreams")
weekly_reports = get_table("weeklyreports")
accomplishments = get_table("accomplishments")
hourstracking = get_table("hourstracking")