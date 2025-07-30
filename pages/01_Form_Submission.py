# pages/01_Form_Submission.py

# Import required libraries
import streamlit as st  # Used to build the interactive web app
import pandas as pd  # Used for working with tabular data
from sqlalchemy import insert  # For database operations
from sqlalchemy.exc import OperationalError
import time
from datetime import datetime  # For working with dates

# Import shared modules
from utils.db import (
    get_engine,
    employees,
    weekly_reports,
    hourstracking,
    accomplishments,
    workstreams,
    load_tables
)

from utils.helpers import (
    get_most_recent_monday,
    get_or_create_employee,
    get_or_create_workstream,
    clean_dataframe_dates_hours,
    normalize_text
)

# Ensure tables are loaded
load_tables()

####################
# --- Page Setup ---
####################
# Configure the layout of the Streamlit page
st.set_page_config(
    # browser tab title
    page_title="Weekly Form Submission", 
    # wide layout for more screen space
    layout="wide")

st.markdown("""
    <style>
        /* Blue Header for titles */
        h1, h2, h3, h4 {
            color: #004080 !important; /* Navy Blue */
        }
        
        /* KPI metric cards */
        div[data-testid="stMetricValue"] {
            color: #004080;
            font-weight: bold;
        }
        div[data-testid="stMetricLabel"] {
            color: #1E90FF;
        }

        /* Horizontal rule */
        hr {
            border-top: 2px solid #1E90FF;
        }
    </style>
""", unsafe_allow_html=True)


# Display logo at top of app (ensure image path points to valid directory)
st.image("images/Iberia-Advisory.png", width=250)

####################################
# --- Page Title and Description ---
####################################
# Display the main title and a short description below it
st.title("Weekly Form Submission Portal")
st.caption("Log your team's contributions and accomplishments for the week.")

#########################
# --- Column Mapping Dictionaries ---
#########################
# These dictionaries map human-readable column names (used in the app) to the actual column names in the database

weekly_report_col_map = {
    "Reporting Week (MM/DD/YYYY)": "weekstartdate",
    "Vendor Name": "vendorname",
    "Division/Command": "divisioncommand",
    "Work Product Title": "workproducttitle",
    "Brief Description of Contribution": "contributiondescription",
    "Work Product Status": "status",
    "Planned or Unplanned (Monthly PMR)": "plannedorunplanned",
    "If Completed (YYYY-MM-DD)": "datecompleted",
    "Distinct NFR": "distinctnfr",
    "Distinct CAP": "distinctcap",
    "Time Spent Hours": "hoursworked",
    "Contractor (Last, First Name)": "contractorname",
    "Govt TA (Last, First Name)": "govttaname",
    "Labor Category": "laborcategory"
}

accomplishments_col_map = {
    "Contractor (Last, First Name)": "name",
    "Reporting Week (MM/DD/YYYY)": "reporting_week",
    "Workstream": "workstream_name",
    "Accomplishment 1": "accomplishment_1",
    "Accomplishment 2": "accomplishment_2",
    "Accomplishment 3": "accomplishment_3",
    "Accomplishment 4": "accomplishment_4",
    "Accomplishment 5": "accomplishment_5"
}

# Create lists of the columns to show in each table editor
weekly_columns = list(weekly_report_col_map.keys())
accom_columns = list(accomplishments_col_map.keys())

# Get most recent Monday for pre-populating the form
most_recent_monday = get_most_recent_monday()

################################
# --- Weekly Reports Section ---
################################
st.markdown("## Weekly Reports")
with st.expander("Instructions", expanded=False):
    st.markdown("""
    - Use **Tab** to move across fields quickly.
    - Enter actual hours worked (up to 40).
    - Leave blank rows empty — they'll be ignored.
    """)
# Create a default empty DataFrame for the user to fill
weekly_default = pd.DataFrame([{col: "" for col in weekly_columns}])
weekly_default.at[0, "Reporting Week (MM/DD/YYYY)"] = most_recent_monday
weekly_default.at[0, "If Completed (YYYY-MM-DD)"] = pd.NaT

# Display an editable table (like an excel spreadsheet)
weekly_df = st.data_editor(
    weekly_default,
    column_config={
        "Reporting Week (MM/DD/YYYY)": st.column_config.DateColumn("Reporting Week"),
        "If Completed (YYYY-MM-DD)": st.column_config.DateColumn("Date Completed"),
    },
    use_container_width=True,
    hide_index=True,
    num_rows="dynamic"
)

# --- Retry Wrapper ---
def with_retry(func, max_attempts=3, delay=2):
    for attempt in range(1, max_attempts + 1):
        try:
            return func()
        except OperationalError as e:
            if attempt < max_attempts:
                st.warning(f"Database connection lost. Retrying ({attempt}/{max_attempts})...")
                time.sleep(delay)
            else:
                raise


######################################
# --- Submit Weekly Reports Button ---
######################################

if st.button("Submit Weekly Reports", key="submit_weekly"):
    cleaned_df = weekly_df.dropna(how="all")
    if cleaned_df.empty:
        st.warning("Please fill at least one row before submitting.")
    else:
        try:
            def insert_weekly():
                df = cleaned_df.rename(columns=weekly_report_col_map)
                df = clean_dataframe_dates_hours(
                    df,
                    date_cols=["weekstartdate", "datecompleted"],
                    numeric_cols=["hoursworked"]
                )
                df["effortpercentage"] = (df["hoursworked"] / 40) * 100
            
                with get_engine().begin() as conn:
                    weekly_data, hours_data, employee_cache = [], [], {}
                    duplicates_found, inserted_count = [], 0
            
                    for _, row in df.iterrows():
                        contractor = normalize_text(row.get("contractorname", ""))
                        if not contractor:
                            continue
            
                        if contractor not in employee_cache:
                            employee_cache[contractor] = get_or_create_employee(
                                conn,
                                contractor_name=contractor,
                                vendor=normalize_text(row.get("vendorname", "")),
                                laborcategory=normalize_text(row.get("laborcategory", ""))
                            )
                        employee_id = employee_cache[contractor]
            
                        # --- Duplicate Check ---
                        existing = conn.execute(
                            weekly_reports.select().where(
                                (weekly_reports.c.EmployeeID == employee_id) &
                                (weekly_reports.c.WeekStartDate == row["weekstartdate"]) &
                                (weekly_reports.c.WorkProductTitle == normalize_text(row.get("workproducttitle", "")))
                            )
                        ).fetchone()
            
                        if existing:
                            duplicates_found.append(row.get("workproducttitle"))
                            continue
            
                        weekly_data.append({
                            "EmployeeID": employee_id,
                            "WeekStartDate": row["weekstartdate"],
                            "DivisionCommand": normalize_text(row.get("divisioncommand", "")),
                            "WorkProductTitle": normalize_text(row.get("workproducttitle", "")),
                            "ContributionDescription": normalize_text(row.get("contributiondescription", "")),
                            "Status": normalize_text(row.get("status", "")),
                            "PlannedOrUnplanned": normalize_text(row.get("plannedorunplanned", "")),
                            "DateCompleted": row["datecompleted"],
                            "DistinctNFR": normalize_text(row.get("distinctnfr", "")),
                            "DistinctCAP": normalize_text(row.get("distinctcap", "")),
                            "EffortPercentage": row["effortpercentage"],
                            "ContractorName": contractor,
                            "GovtTAName": normalize_text(row.get("govttaname", "")),
                        })
                        inserted_count += 1
            
                        if row["hoursworked"] > 0:
                            hours_data.append({
                                "EmployeeID": employee_id,
                                "WorkstreamID": None,
                                "ReportingWeek": row["weekstartdate"],
                                "HoursWorked": row["hoursworked"],
                                "LevelOfEffort": row["effortpercentage"],
                            })
            
                    if weekly_data:
                        conn.execute(insert(weekly_reports), weekly_data)
                    if hours_data:
                        conn.execute(insert(hourstracking), hours_data)
            
                msg = f"Weekly Reports submitted: {inserted_count}."
                if duplicates_found:
                    msg += f" Skipped {len(duplicates_found)} duplicates."
                st.success(msg)

            with_retry(insert_weekly)
            st.success("Weekly Reports submitted successfully!")
            st.session_state["weekly_df"] = pd.DataFrame([{col: "" for col in weekly_columns}])  # Clear form
        except Exception as e:
            st.error(f"Error inserting weekly reports: {e}")



##################################
# --- Accomplishments Section ---
##################################
st.markdown("---")
st.markdown("## Weekly Accomplishments")
with st.expander("Instructions", expanded=False):
    st.markdown("""
    - Each row represents one contractor's accomplishments for the week.
    - Up to 5 accomplishments per person.
    - Leave unused fields blank.
    """)

# Create a default blank row for accomplishments entry
accom_default = pd.DataFrame([{col: "" for col in accom_columns}])
accom_default.at[0, "Reporting Week (MM/DD/YYYY)"] = most_recent_monday

# Display editable table for accomplishments
accom_df = st.data_editor(
    accom_default,
    column_config={
        "Reporting Week (MM/DD/YYYY)": st.column_config.DateColumn("Reporting Week"),
    },
    use_container_width=True,
    hide_index=True,
    num_rows="dynamic"
)

#######################################
# --- Submit Accomplishments Button ---
#######################################
if st.button("Submit Accomplishments", key="submit_accom"):
    cleaned_accom_df = accom_df.dropna(how="all")
    if cleaned_accom_df.empty:
        st.warning("Please fill at least one row of accomplishments.")
    else:
        try:
            def insert_accomplishments():
                df = cleaned_accom_df.rename(columns=accomplishments_col_map)
                duplicates_found, inserted_count = [], 0

                with get_engine().begin() as conn:
                    employee_cache, workstream_cache = {}, {}
                    for _, row in df.iterrows():
                        contractor = normalize_text(row.get("name", ""))
                        if not contractor:
                            continue
                        if contractor not in employee_cache:
                            employee_cache[contractor] = get_or_create_employee(conn, contractor)
                        employee_id = employee_cache[contractor]

                        workstream_name = normalize_text(row.get("workstream_name", ""))
                        if workstream_name not in workstream_cache:
                            workstream_cache[workstream_name] = get_or_create_workstream(conn, workstream_name)
                        workstream_id = workstream_cache[workstream_name]

                        reporting_week = (
                            pd.to_datetime(row.get("reporting_week"), errors='coerce').date()
                            if pd.notnull(row.get("reporting_week")) else None
                        )

                        for i in range(1, 6):
                            text = normalize_text(row.get(f"accomplishment_{i}", ""))
                            if text:
                                existing = conn.execute(
                                    accomplishments.select().where(
                                        (accomplishments.c.EmployeeID == employee_id) &
                                        (accomplishments.c.WorkstreamID == workstream_id) &
                                        (accomplishments.c.DateRange == reporting_week) &
                                        (accomplishments.c.Description == text)
                                    )
                                ).fetchone()

                                if existing:
                                    duplicates_found.append(text)
                                    continue

                                conn.execute(insert(accomplishments).values(
                                    EmployeeID=employee_id,
                                    WorkstreamID=workstream_id,
                                    DateRange=reporting_week,
                                    Description=text
                                ))
                                inserted_count += 1

                msg = f"Accomplishments submitted: {inserted_count}."
                if duplicates_found:
                    msg += f" Skipped {len(duplicates_found)} duplicates."
                st.success(msg)

            with_retry(insert_accomplishments)
            st.session_state["accom_df"] = pd.DataFrame([{col: "" for col in accom_columns}])  # Clear form
        except Exception as e:
            st.error(f"Error inserting accomplishments: {e}")
            
            
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
