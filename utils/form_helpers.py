# utils/form_helpers.py
import pandas as pd
from datetime import datetime, timezone
from utils.helpers import (
    normalize_text,
    get_or_create_employee,
    get_or_create_workstream
)
from utils.db import insert_row

def validate_required_fields(df: pd.DataFrame, required_fields: list) -> list:
    """
    Checks for missing required fields in DataFrame rows.
    Returns a list of row indices (1-based) that are missing data.
    """
    missing_rows = []
    for idx, row in df.iterrows():
        if any(not str(row.get(field, "")).strip() for field in required_fields):
            missing_rows.append(idx + 1)
    return missing_rows

def insert_batch_accomplishments(conn, df: pd.DataFrame, existing_accomplishments: pd.DataFrame) -> tuple:
    """
    Inserts accomplishments in batch mode with caching and duplicate detection.
    Returns tuple: (inserted_count, duplicates_skipped)
    """
    employee_cache, workstream_cache = {}, {}
    duplicates = []
    inserted = 0

    for _, row in df.iterrows():
        contractor = normalize_text(row["name"])
        workstream_name = normalize_text(row["workstream_name"])
        reporting_week = (
            pd.to_datetime(row["reporting_week"], errors="coerce").date()
            if pd.notnull(row["reporting_week"]) else None
        )

        # Resolve Employee
        if contractor not in employee_cache:
            employee_cache[contractor] = get_or_create_employee(conn=conn, contractor_name=contractor)
        employee_id = employee_cache[contractor]

        # Resolve Workstream
        if workstream_name not in workstream_cache:
            workstream_cache[workstream_name] = get_or_create_workstream(conn=conn, workstream_name=workstream_name)
        workstream_id = workstream_cache[workstream_name]

        # Insert up to 5 accomplishments
        for i in range(1, 6):
            desc = normalize_text(row.get(f"accomplishment_{i}", ""))
            if not desc:
                continue

            # Duplicate check
            duplicate_check = existing_accomplishments[
                (existing_accomplishments["EmployeeID"] == employee_id) &
                (existing_accomplishments["WorkstreamID"] == workstream_id) &
                (existing_accomplishments["DateRange"] == reporting_week) &
                (existing_accomplishments["Description"].str.lower() == desc.lower())
            ]
            if not duplicate_check.empty:
                duplicates.append(desc)
                continue

            insert_row("Accomplishments", {
                "EmployeeID": employee_id,
                "WorkstreamID": workstream_id,
                "DateRange": reporting_week,
                "Description": desc,
                "CreatedAt": datetime.now(timezone.utc),
                "EnteredBy": "anonymous"
            })
            inserted += 1

    return inserted, duplicates
