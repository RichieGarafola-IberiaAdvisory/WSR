# Every page can simply from utils.db import engine, employees, workstreams, weekly_reports, accomplishments, hours tracking
# Avoids repeating schema reflection and config.

from sqlalchemy import create_engine, MetaData

# Use direct connection string (as per your instruction)
DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/Iberia_BackOffice"

# Create engine and reflect schema metadata
engine = create_engine(DATABASE_URL, echo=False)
metadata = MetaData()
metadata.reflect(bind=engine)

# Table references (lazy-loaded)
employees = metadata.tables["employees"]
workstreams = metadata.tables["workstreams"]
weekly_reports = metadata.tables["weeklyreports"]
accomplishments = metadata.tables["accomplishments"]
hourstracking = metadata.tables["hourstracking"]
