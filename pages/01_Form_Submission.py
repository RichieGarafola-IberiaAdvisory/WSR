# pages/01_Form_Submission.py

import streamlit as st
import pandas as pd
from sqlalchemy.exc import OperationalError
from sqlalchemy import Table, MetaData, text
import sys, os
from datetime import datetime, timezone
from utils.db import (
    get_engine,
    get_data,
    insert_row,
    get_session_data
)
from utils.helpers import (
    get_most_recent_monday,
    get_or_create_employee,
    get_or_create_workstream,
    clean_dataframe_dates_hours,
    normalize_text
)

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

####################
# --- Page Setup ---
####################
st.set_page_config(page_title="Weekly Form Submission", layout="wide")
st.image("images/Iberia-Advisory.png", width=250)

st.title("Weekly Form Submission Portal")
st.caption("Each contractor must have exactly 5 accomplishments per week.")

# Load cached session data
try:
    session_data = get_session_data()
except Exception:
    st.error("⚠️ Database is currently offline. Submissions cannot be saved.")
    session_data = None

# --- Column Mapping ---
weekly_report_col_map = {
    "Reporting Week (MM/DD/YYYY)": "weekstartdate",
    "Vendor Name": "vendorname",
    "Division/Command": "divisioncommand",
    "Workstream": "workstream_name",
    "Work Product Title": "workproducttitle",
    "Work Product Status": "status",
    "Planned or Unplanned": "plannedorunplanned",
    "If Completed (YYYY-MM-DD)": "datecompleted",
    "Distinct NFR": "distinctnfr",
    "Distinct CAP": "distinctcap",
    "Time Spent Hours": "hoursworked",
    "Contractor (Last, First Name)": "contractorname",
    "Govt TA (Last, First Name)": "govttaname",
    "Labor Category": "laborcategory",
    "Accomplishment 1": "accomplishment1",
    "Accomplishment 2": "accomplishment2",
    "Accomplishment 3": "accomplishment3",
    "Accomplishment 4": "accomplishment4",
    "Accomplishment 5": "accomplishment5",
}

weekly_columns = list(weekly_report_col_map.keys())

# Default row
most_recent_monday = get_most_recent_monday()
weekly_default = pd.DataFrame([{col: "" for col in weekly_columns}])
weekly_default.at[0, "Reporting Week (MM/DD/YYYY)"] = most_recent_monday
weekly_default.at[0, "If Completed (YYYY-MM-DD)"] = pd.NaT

# Editable table
disabled = session_data is None
weekly_df = st.data_editor(
    weekly_default,
    column_config={
        "Reporting Week (MM/DD/YYYY)": st.column_config.DateColumn("Reporting Week"),
        "If Completed (YYYY-MM-DD)": st.column_config.DateColumn("Date Completed"),
    },
    use_container_width=True,
    hide_index=True,
    num_rows="dynamic",
    disabled=disabled
)

st.caption("ℹ️ Tip: Each contractor can submit multiple work products per week, "
           "but must have exactly 5 accomplishments total. ")
           # "The table below will highlight incomplete or excessive entries.")

def highlight_rows(row):
    mapped = row.rename(index=weekly_report_col_map).rename(index=str.lower)
    total_accomplishments = sum(
        pd.notna(mapped.get(f"accomplishment{i}", None)) and mapped.get(f"accomplishment{i}") != ""
        for i in range(1, 6)
    )
    
    # Green = complete, Yellow = incomplete, Red = exceeds
    if total_accomplishments == 5:
        return ['background-color: #d4edda'] * len(row)
    elif total_accomplishments > 5:
        return ['background-color: #f8d7da'] * len(row)
    else:
        return ['background-color: #fff3cd'] * len(row)

# styled_df = weekly_df.style.apply(highlight_rows, axis=1)
# st.dataframe(styled_df, use_container_width=True)

###############################
# Live Accomplishment Counter
###############################
def count_accomplishments(df):
    mapped = df.rename(columns=weekly_report_col_map).rename(columns=str.lower)
    grouped = (
        mapped.groupby(["contractorname", "weekstartdate"])[[f"accomplishment{i}" for i in range(1, 6)]]
        .apply(lambda g: g.notna().sum().sum())
    )
    return grouped

if not weekly_df.empty:
    counts = count_accomplishments(weekly_df)
    for (contractor, week), total in counts.items():
        if total < 5:
            st.warning(f"⚠{contractor} ({week}) has only {total}/5 accomplishments.")
        elif total > 5:
            st.error(f"{contractor} ({week}) exceeds 5 accomplishments with {total}.")
        else:
            st.info(f"{contractor} ({week}) has exactly 5 accomplishments.")


########################
# --- Retry Helper ---
########################
def with_retry(func, max_attempts=3, delay=2):
    for attempt in range(1, max_attempts + 1):
        try:
            return func()
        except OperationalError:
            if attempt < max_attempts:
                st.warning(f"Database connection lost. Retrying ({attempt}/{max_attempts})...")
                time.sleep(delay)
            else:
                raise

######################################
# --- Submit Weekly Reports Button ---
######################################
def validate_accomplishments(df):
    """
    Ensures each contractor has at least 5 accomplishments total for each week.
    """
    required_cols = {"contractorname", "weekstartdate"} | {
        f"accomplishment{i}" for i in range(1, 6)
    }
    
    # Fill any missing expected columns with None
    for col in required_cols:
        if col not in df.columns:
            df[col] = None

    grouped = (
        df.groupby(["contractorname", "weekstartdate"])[[f"accomplishment{i}" for i in range(1, 6)]]
        .apply(lambda g: g.notna().sum().sum())
        .reset_index(name="total_accomplishments")
    )

    return grouped[grouped["total_accomplishments"] != 5]


# --- Check if all contractors have exactly 5 accomplishments ---
mapped_for_validation = weekly_df.rename(columns=weekly_report_col_map).rename(columns=str.lower)
invalid_rows = validate_accomplishments(mapped_for_validation)

# Disable submit if required fields are missing
def has_required_fields(df):
    required = ["Contractor (Last, First Name)", "Vendor Name", "Labor Category", "Workstream"]
    for field in required:
        if df[field].isna().all() or (df[field] == "").all():
            return False
    return True

# Update form_ready logic
form_ready = (
    invalid_rows.empty
    and not weekly_df.dropna(how="all").empty
    and has_required_fields(weekly_df)
)

if st.button("Submit Weekly Reports", key="submit_weekly", disabled=not form_ready):
    if session_data is None:
        st.warning("⚠️ Database is offline. Please try again later.")
    else:
        cleaned_df = weekly_df.dropna(how="all")
        if cleaned_df.empty:
            st.warning("Please fill at least one row before submitting.")
        else:
            mapped_cleaned = cleaned_df.rename(columns=weekly_report_col_map).rename(columns=str.lower)
            invalid = validate_accomplishments(mapped_cleaned)

            if not invalid.empty:
                st.error(
                    "🚨 Submission blocked: "
                    + "; ".join(
                        f"{row['contractorname']} (Week {row['weekstartdate']}) "
                        f"has only {row['total_accomplishments']} accomplishments"
                        for _, row in invalid.iterrows()
                    )
                )
            else:
                try:
                    def insert_weekly():
                        metadata = MetaData()
                        engine = get_engine()
                        weekly_table = Table("WeeklyReports", metadata, autoload_with=engine)
                        hours_table = Table("HoursTracking", metadata, autoload_with=engine)

                        df = cleaned_df.rename(columns=weekly_report_col_map)
                        df = clean_dataframe_dates_hours(
                            df,
                            date_cols=["weekstartdate", "datecompleted"],
                            numeric_cols=["hoursworked"]
                        )
                        df["effortpercentage"] = (df["hoursworked"] / 40) * 100

                        with engine.begin() as conn:
                            existing_keys = set(
                                conn.execute(
                                    text("SELECT EmployeeID, WeekStartDate, WorkProductTitle FROM WeeklyReports")
                                ).fetchall()
                            )

                            weekly_data, hours_data = [], []
                            employee_cache, workstream_cache = {}, {}
                            duplicates, invalid_rows, inserted_rows = [], [], []

                            for idx, row in df.iterrows():
                                required_fields = ["contractorname", "vendorname", "laborcategory", "workstream_name"]
                                missing = any(pd.isna(row[f]) or row[f] == "" for f in required_fields)

                                contractor = row['contractorname']
                                if contractor not in employee_cache:
                                    emp_id = get_or_create_employee(
                                        contractor_name=contractor,
                                        vendor=normalize_text(row['vendorname']),
                                        laborcategory=normalize_text(row['laborcategory'])
                                    )
                                    employee_cache[contractor] = emp_id
                                else:
                                    emp_id = employee_cache[contractor]

                                ws_name = normalize_text(row['workstream_name'])
                                if ws_name not in workstream_cache:
                                    ws_id = get_or_create_workstream(conn=conn, workstream_name=ws_name)
                                    workstream_cache[ws_name] = ws_id
                                else:
                                    ws_id = workstream_cache[ws_name]

                                key = (emp_id, row['weekstartdate'], normalize_text(row.get("workproducttitle", "")))

                                accomplishments = [
                                    normalize_text(row[f"accomplishment{i}"])
                                    for i in range(1, 6)
                                    if pd.notna(row[f"accomplishment{i}"]) and row[f"accomplishment{i}"] != ""
                                ]

                                if key in existing_keys:
                                    duplicates.append(row)
                                    continue
                                if missing or emp_id is None or ws_id is None or len(accomplishments) != 5:
                                    invalid_rows.append(row)
                                    continue

                                contribution_description = "; ".join(accomplishments)

                                def safe_val(value):
                                    return normalize_text(value) if pd.notna(value) else "N/A"

                                weekly_data.append({
                                    "EmployeeID": emp_id,
                                    "WorkstreamID": ws_id,
                                    "WeekStartDate": row["weekstartdate"],
                                    "DivisionCommand": safe_val(row.get("divisioncommand", "")),
                                    "WorkProductTitle": safe_val(row.get("workproducttitle", "")),
                                    "ContributionDescription": contribution_description,
                                    "Status": safe_val(row.get("status", "")),
                                    "PlannedOrUnplanned": safe_val(row.get("plannedorunplanned", "")),
                                    "DateCompleted": row["datecompleted"],
                                    "DistinctNFR": safe_val(row.get("distinctnfr", "")),
                                    "DistinctCAP": safe_val(row.get("distinctcap", "")),
                                    "EffortPercentage": row["effortpercentage"],
                                    "ContractorName": contractor,
                                    "GovtTAName": safe_val(row.get("govttaname", "")),
                                    "Accomplishment1": safe_val(row.get("accomplishment1", "")),
                                    "Accomplishment2": safe_val(row.get("accomplishment2", "")),
                                    "Accomplishment3": safe_val(row.get("accomplishment3", "")),
                                    "Accomplishment4": safe_val(row.get("accomplishment4", "")),
                                    "Accomplishment5": safe_val(row.get("accomplishment5", "")),
                                    "CreatedAt": datetime.now(timezone.utc),
                                    "EnteredBy": "anonymous"
                                })

                                if pd.notna(row["hoursworked"]) and row["hoursworked"] > 0:
                                    hours_data.append({
                                        "EmployeeID": emp_id,
                                        "WorkstreamID": ws_id,
                                        "ReportingWeek": row["weekstartdate"],
                                        "HoursWorked": row["hoursworked"],
                                        "LevelOfEffort": row["effortpercentage"],
                                        "CreatedAt": datetime.now(timezone.utc),
                                        "EnteredBy": "anonymous"
                                    })
                                inserted_rows.append(row)

                            if weekly_data:
                                conn.execute(weekly_table.insert(), weekly_data)
                            if hours_data:
                                conn.execute(hours_table.insert(), hours_data)

                        if inserted_rows:
                            st.success(f"✅ {len(inserted_rows)} reports submitted successfully.")
                        if duplicates:
                            st.info(f"ℹ️ {len(duplicates)} duplicates skipped.")
                            st.dataframe(pd.DataFrame(duplicates))
                        if invalid_rows:
                            st.warning(f"🚫 {len(invalid_rows)} reports skipped due to missing fields or accomplishments.")
                            st.dataframe(pd.DataFrame(invalid_rows))
                            st.session_state["weekly_df"] = pd.DataFrame(invalid_rows)
                        else:
                            st.session_state["weekly_df"] = pd.DataFrame([{col: "" for col in weekly_columns}])

                    with_retry(insert_weekly)
                    session_data = get_session_data()
                except Exception as e:
                    st.error(f"Database insert failed: {type(e).__name__} - {e}")


########################################
# Helper function for testing purposes 
#######################################

def submit_form(name, vendor, labor_category, week_ending):
    """Helper for tests to simulate a form submission."""
    from utils import helpers
    if not name.strip() or not vendor or not labor_category or not week_ending:
        return False

    import datetime
    try:
        if isinstance(week_ending, str):
            datetime.datetime.strptime(week_ending, "%Y-%m-%d")
    except Exception:
        return False

    emp_id = helpers.get_or_create_employee(None, name, vendor, labor_category)
    if not emp_id:
        return False

    return helpers.insert_weekly_report({
        "EmployeeID": emp_id,
        "WeekStartDate": week_ending
    })


            
#######################        
# --- Internal Note ---
#######################

##############################################################
##############################################################
# This app was designed by Richie Garafola July 2025.
# Any questions or issues please reach out.
# 631.433.6400
# RGarafola@IberiaAdvisory.com
# RichieGarafola@hotmail.com
# www.linkedin.com/in/richiegarafola
##############################################################
##############################################################
