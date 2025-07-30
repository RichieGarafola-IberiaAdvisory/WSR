# pages/01_Form_Submission.py

# Import required libraries
import streamlit as st  # Used to build the interactive web app
import pandas as pd  # Used for working with tabular data
from sqlalchemy import insert  # For database operations
from sqlalchemy.exc import OperationalError
import time
from datetime import datetime  # For working with dates

# Import shared modules
from utils.db import get_engine, employees, weekly_reports, hourstracking, accomplishments

from utils.helpers import (
    get_most_recent_monday,
    get_or_create_employee,
    get_or_create_workstream,
    clean_dataframe_dates_hours,
    normalize_text
)

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
    st.markdown("- Use Tab to move across fields quickly.\n- Enter actual hours worked (up to 40).")

weekly_default = pd.DataFrame([{col: "" for col in weekly_columns}])
weekly_default.at[0, "Reporting Week (MM/DD/YYYY)"] = most_recent_monday
weekly_default.at[0, "If Completed (YYYY-MM-DD)"] = pd.NaT

weekly_df = st.data_editor(
    st.session_state.get("weekly_df", weekly_default),
    column_config={
        "Reporting Week (MM/DD/YYYY)": st.column_config.DateColumn("Reporting Week"),
        "If Completed (YYYY-MM-DD)": st.column_config.DateColumn("Date Completed"),
    },
    use_container_width=True,
    hide_index=True,
    num_rows="dynamic"
)

if st.button("Submit Weekly Reports"):
    def insert_weekly():
        df = weekly_df.dropna(how="all").rename(columns=weekly_report_col_map)
        if df.empty:
            st.warning("Please fill at least one row.")
            return

        df = clean_dataframe_dates_hours(df, ["weekstartdate", "datecompleted"], ["hoursworked"])
        df["effortpercentage"] = (df["hoursworked"] / 40) * 100

        # Bulk resolve employees
        contractors = df["contractorname"].dropna().unique()
        with get_engine().begin() as conn:
            existing = conn.execute(
                select([employees.c.Name, employees.c.EmployeeID])
                .where(employees.c.Name.in_(contractors))
            ).fetchall()
            emp_map = {normalize_text(e.Name): e.EmployeeID for e in existing}

            # Create missing employees
            missing = [c for c in contractors if normalize_text(c) not in emp_map]
            if missing:
                conn.execute(insert(employees), [{"Name": normalize_text(m)} for m in missing])
                new_rows = conn.execute(
                    select([employees.c.Name, employees.c.EmployeeID])
                    .where(employees.c.Name.in_(missing))
                ).fetchall()
                emp_map.update({normalize_text(e.Name): e.EmployeeID for e in new_rows})

            # Weekly & hours data
            weekly_data = df.apply(lambda row: {
                "EmployeeID": emp_map[normalize_text(row["contractorname"])],
                "WeekStartDate": row["weekstartdate"],
                "DivisionCommand": normalize_text(row["divisioncommand"]),
                "WorkProductTitle": normalize_text(row["workproducttitle"]),
                "ContributionDescription": normalize_text(row["contributiondescription"]),
                "Status": normalize_text(row["status"]),
                "PlannedOrUnplanned": normalize_text(row["plannedorunplanned"]),
                "DateCompleted": row["datecompleted"],
                "DistinctNFR": normalize_text(row["distinctnfr"]),
                "DistinctCAP": normalize_text(row["distinctcap"]),
                "EffortPercentage": row["effortpercentage"],
                "ContractorName": normalize_text(row["contractorname"]),
                "GovtTAName": normalize_text(row["govttaname"]),
            }, axis=1).tolist()

            hours_data = df[df["hoursworked"] > 0].apply(lambda row: {
                "EmployeeID": emp_map[normalize_text(row["contractorname"])],
                "WorkstreamID": None,
                "ReportingWeek": row["weekstartdate"],
                "HoursWorked": row["hoursworked"],
                "LevelOfEffort": row["effortpercentage"],
            }, axis=1).tolist()

            if weekly_data:
                conn.execute(insert(weekly_reports), weekly_data)
            if hours_data:
                conn.execute(insert(hourstracking), hours_data)

    with_retry(insert_weekly)
    st.success("Weekly Reports submitted successfully!")
    st.session_state["weekly_df"] = weekly_default.copy()



##################################
# --- Accomplishments Section ---
##################################
st.markdown("---")
st.markdown("## Weekly Accomplishments")
with st.expander("Instructions", expanded=False):
    st.markdown("- Each row represents one contractor's accomplishments for the week.\n- Up to 5 accomplishments per person.")

accom_default = pd.DataFrame([{col: "" for col in accom_columns}])
accom_default.at[0, "Reporting Week (MM/DD/YYYY)"] = most_recent_monday

accom_df = st.data_editor(
    st.session_state.get("accom_df", accom_default),
    column_config={
        "Reporting Week (MM/DD/YYYY)": st.column_config.DateColumn("Reporting Week"),
    },
    use_container_width=True,
    hide_index=True,
    num_rows="dynamic"
)

def hash_description(desc):
    return hashlib.sha256(desc.encode("utf-8")).hexdigest().upper()

if st.button("Submit Accomplishments"):
    def insert_accomplishments():
        df = accom_df.dropna(how="all").rename(columns=accomplishments_col_map)
        if df.empty:
            st.warning("Please fill at least one row.")
            return

        # Flatten accomplishments
        accom_rows = []
        for _, row in df.iterrows():
            for i in range(1, 6):
                text = normalize_text(row.get(f"accomplishment_{i}", ""))
                if text:
                    accom_rows.append({
                        "name": normalize_text(row["name"]),
                        "workstream": normalize_text(row["workstream_name"]),
                        "date": pd.to_datetime(row["reporting_week"], errors="coerce").date(),
                        "description": text,
                        "hash": hash_description(text),
                    })
        accom_df_flat = pd.DataFrame(accom_rows)

        # Resolve employees and workstreams
        with get_engine().begin() as conn:
            emp_names = accom_df_flat["name"].unique()
            ws_names = accom_df_flat["workstream"].unique()

            emp_existing = conn.execute(
                select([employees.c.Name, employees.c.EmployeeID])
                .where(employees.c.Name.in_(emp_names))
            ).fetchall()
            emp_map = {normalize_text(e.Name): e.EmployeeID for e in emp_existing}

            ws_existing = conn.execute(
                select([workstreams.c.Name, workstreams.c.WorkstreamID])
                .where(workstreams.c.Name.in_(ws_names))
            ).fetchall()
            ws_map = {normalize_text(w.Name): w.WorkstreamID for w in ws_existing}

            # Create missing
            missing_emp = [e for e in emp_names if normalize_text(e) not in emp_map]
            if missing_emp:
                conn.execute(insert(employees), [{"Name": normalize_text(e)} for e in missing_emp])
                new_rows = conn.execute(
                    select([employees.c.Name, employees.c.EmployeeID])
                    .where(employees.c.Name.in_(missing_emp))
                ).fetchall()
                emp_map.update({normalize_text(e.Name): e.EmployeeID for e in new_rows})

            missing_ws = [w for w in ws_names if normalize_text(w) not in ws_map]
            if missing_ws:
                conn.execute(insert(workstreams), [{"Name": normalize_text(w)} for w in missing_ws])
                new_ws = conn.execute(
                    select([workstreams.c.Name, workstreams.c.WorkstreamID])
                    .where(workstreams.c.Name.in_(missing_ws))
                ).fetchall()
                ws_map.update({normalize_text(w.Name): w.WorkstreamID for w in new_ws})

            # Check existing hashes
            existing = conn.execute(
                select([accomplishments.c.EmployeeID, accomplishments.c.WorkstreamID,
                        accomplishments.c.DateRange, accomplishments.c.DescriptionHash])
                .where(accomplishments.c.EmployeeID.in_([emp_map[n] for n in emp_map]))
            ).fetchall()
            existing_set = {(e.EmployeeID, e.WorkstreamID, e.DateRange, e.DescriptionHash) for e in existing}

            new_data = []
            for _, r in accom_df_flat.iterrows():
                key = (
                    emp_map[normalize_text(r["name"])],
                    ws_map[normalize_text(r["workstream"])],
                    r["date"],
                    r["hash"]
                )
                if key not in existing_set:
                    new_data.append({
                        "EmployeeID": key[0],
                        "WorkstreamID": key[1],
                        "DateRange": key[2],
                        "Description": r["description"]
                    })

            if new_data:
                conn.execute(insert(accomplishments), new_data)

    with_retry(insert_accomplishments)
    st.success("Accomplishments submitted successfully!")
    st.session_state["accom_df"] = accom_default.copy()
          
            
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
