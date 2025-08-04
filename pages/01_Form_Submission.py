# pages/01_Form_Submission.py

# Import required libraries
import streamlit as st  # Used to build the interactive web app
import pandas as pd  # Used for working with tabular data
from sqlalchemy import insert  # For database operations
from sqlalchemy.exc import OperationalError
import time
import sys, os
from datetime import datetime, timezone  # For working with dates

# Import shared modules
# from utils.db import (
#     get_engine,
#     employees,
#     weekly_reports,
#     hourstracking,
#     accomplishments,
#     workstreams,
#     load_tables,
#     get_session_data
# )

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
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
    normalize_text,
    insert_weekly_report,
    insert_accomplishment
)

from utils.form_helpers import validate_required_fields, insert_batch_accomplishments

# Ensure tables are loaded
# load_tables()

# Load cached session data (only fetches DB if cache expired or cleared)
try:
    session_data = get_session_data()
    from utils.db import load_table
    employees_df = load_table("Employees")
    weekly_reports_df = load_table("WeeklyReports")

except Exception:
    st.error("⚠️ Database is currently offline. You can still fill out the forms, "
             "but submissions will not be saved until the database is restored.")
    session_data = None


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

if st.button("Submit Accomplishments", key="submit_accom"):
    if session_data is None:
        st.warning("⚠️ Database is offline. Please try again later.")
    else:
        cleaned_accom_df = accom_df.dropna(how="all")

        if cleaned_accom_df.empty:
            st.warning("Please fill at least one row of accomplishments.")
        else:
            # ✅ Check for required fields
            from utils.form_helpers import validate_required_fields, insert_batch_accomplishments

            missing_rows = validate_required_fields(
                cleaned_accom_df,
                ["Contractor (Last, First Name)", "Workstream"]
            )

            if missing_rows:
                st.error(
                    f"⚠️ The following row(s) are missing required fields: "
                    f"{', '.join(map(str, missing_rows))}. "
                    "Please review and complete these rows."
                )
            else:
                try:
                    def insert_accomplishments():
                        df = cleaned_accom_df.rename(columns=accomplishments_col_map)
                        existing = get_data("Accomplishments")

                        with get_engine().begin() as conn:
                            inserted, duplicates = insert_batch_accomplishments(conn, df, existing)

                        msg = f"Accomplishments submitted: {inserted}."
                        if duplicates:
                            msg += f" Skipped {len(duplicates)} duplicates."
                        st.success(msg)

                    with_retry(insert_accomplishments)
                    st.session_state["accom_df"] = pd.DataFrame([{col: "" for col in accom_columns}])
                except Exception as e:
                    st.error(f"Database insert failed: {type(e).__name__} - {e}")



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
    if session_data is None:
        st.warning("⚠️ Database is offline. Please try again later.")
    else:
        cleaned_accom_df = accom_df.dropna(how="all")

        if cleaned_accom_df.empty:
            st.warning("Please fill at least one row of accomplishments.")
        else:
            # Validate required fields
            missing_rows = validate_required_fields(
                cleaned_accom_df,
                ["Contractor (Last, First Name)", "Workstream"]
            )

            if missing_rows:
                st.error(
                    f"⚠️ The following row(s) are missing required fields: "
                    f"{', '.join(map(str, missing_rows))}. "
                    "Please review and complete these rows."
                )
            else:
                try:
                    def insert_accomplishments():
                        df = cleaned_accom_df.rename(columns=accomplishments_col_map)
                        existing_accomplishments = get_data("Accomplishments")

                        with get_engine().begin() as conn:
                            inserted_count, duplicates = insert_batch_accomplishments(
                                conn, df, existing_accomplishments
                            )

                        msg = f"Accomplishments submitted: {inserted_count}."
                        if duplicates:
                            msg += f" Skipped {len(duplicates)} duplicates."
                        st.success(msg)

                    with_retry(insert_accomplishments)
                    st.session_state["accom_df"] = pd.DataFrame([{col: "" for col in accom_columns}])  # Reset form

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
