# pages/01_Form_Submission.py

# Import required libraries
import streamlit as st  # Used to build the interactive web app
import pandas as pd  # Used for working with tabular data
from sqlalchemy import create_engine, MetaData, Table, select, insert, func  # For database operations
from datetime import date, timedelta  # For working with dates

# Import shared modules
from utils.db import engine, employees, weekly_reports, hourstracking, accomplishments, load_tables
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

# Display logo at top of app (ensure image path points to valid directory)
st.image("images/Iberia-Advisory.png", width=250)

# Load global tables
load_tables()
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


######################################
# --- Submit Weekly Reports Button ---
######################################

if st.button("📤 Submit Weekly Reports"):
    # Remove entirely empty rows
    cleaned_df = weekly_df.dropna(how="all")
    if cleaned_df.empty:
        st.warning("Please fill at least one row before submitting.")
    else:
        try:
            # Rename columns to match database column names
            cleaned_df = cleaned_df.rename(columns=weekly_report_col_map)
            
            # Ensure dates and hours are properly formatted
            cleaned_df = clean_dataframe_dates_hours(
                cleaned_df,
                date_cols=["weekstartdate", "datecompleted"],
                numeric_cols=["hoursworked"]
            )
            # Compute effort percentage
            cleaned_df["effortpercentage"] = (cleaned_df["hoursworked"] / 40) * 100

            # Begin database transaction
            with engine.begin() as conn:
                for _, row in cleaned_df.iterrows():
                    contractor = normalize_text(row.get("contractorname", "")).replace(" ", "")
                    if not contractor:
                        
                        # Skip empty contractors
                        continue

                    employee_id = get_or_create_employee(
                        conn,
                        contractor_name=contractor,
                        vendor=normalize_text(row.get("vendorname", "")),
                        laborcategory=normalize_text(row.get("laborcategory", ""))
                    )

                    # Insert Weekly Report
                    conn.execute(
                        insert(weekly_reports).values(
                            employeeid=employee_id,
                            weekstartdate=row["weekstartdate"],
                            divisioncommand=normalize_text(row.get("divisioncommand", "")),
                            workproducttitle=normalize_text(row.get("workproducttitle", "")),
                            contributiondescription=normalize_text(row.get("contributiondescription", "")),
                            status=normalize_text(row.get("status", "")),
                            plannedorunplanned=row.get("plannedorunplanned", "").strip().lower(),
                            datecompleted=row["datecompleted"],
                            distinctnfr=normalize_text(row.get("distinctnfr", "")),
                            distinctcap=normalize_text(row.get("distinctcap", "")),
                            effortpercentage=row["effortpercentage"],
                            contractorname=contractor,
                            govttaname=normalize_text(row.get("govttaname", "")),
                            
                            
                            # Audit fields
                            created_at=datetime.utcnow(),
                            entered_by=st.session_state.get("username", "anonymous"),  # or a fallback string
                            source_file="manual_form_submission"
                        )
                    )

                    # Insert Hours Tracking
                    if row["hoursworked"] > 0:
                        conn.execute(
                            insert(hourstracking).values(
                                employeeid=employee_id,
                                workstreamid=None,
                                reportingweek=row["weekstartdate"],
                                hoursworked=row["hoursworked"],
                                levelofeffort=row["effortpercentage"],
                                
                                # Audit fields
                                created_at=datetime.utcnow(),
                                entered_by=st.session_state.get("username", "anonymous"),
                                source_file="manual_form_submission"
                            ))

            st.success("✅ Weekly Reports submitted successfully!")
            # Show the submitted data
            with st.expander("View Submitted Data"):
                st.dataframe(cleaned_df)

        except Exception as e:
            st.error(f"❌ Error inserting weekly reports: {e}")

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
from sqlalchemy import select

if st.button("Submit Accomplishments"):
    cleaned_accom_df = accom_df.dropna(how="all")
    if cleaned_accom_df.empty:
        st.warning("Please fill at least one row of accomplishments.")
    else:
        try:
            df = cleaned_accom_df.rename(columns=accomplishments_col_map)
            duplicates_found = []  # Store skipped duplicates
            inserted_count = 0

            with engine.begin() as conn:
                for _, row in df.iterrows():
                    contractor = normalize_text(row.get("name", ""))
                    if not contractor:
                        continue

                    employee_id = get_or_create_employee(conn, contractor)
                    workstream_id = get_or_create_workstream(
                        conn,
                        normalize_text(row.get("workstream_name", ""))
                    )

                    reporting_week = row.get("reporting_week")
                    week_date = (
                        pd.to_datetime(reporting_week, errors="coerce").date()
                        if pd.notnull(reporting_week)
                        else None
                    )

                    # Check each accomplishment
                    for i in range(1, 6):
                        text = normalize_text(row.get(f"accomplishment_{i}", ""))
                        if text:
                            existing = conn.execute(
                                select(accomplishments).where(
                                    accomplishments.c.EmployeeID == employee_id,
                                    accomplishments.c.WorkstreamID == workstream_id,
                                    accomplishments.c.DateRange == week_date,
                                    accomplishments.c.Description == text
                                )
                            ).fetchone()

                            if existing:
                                duplicates_found.append(text)
                                continue  # Skip duplicate

                            conn.execute(insert(accomplishments).values(
                                EmployeeID=employee_id,
                                WorkstreamID=workstream_id,
                                DateRange=week_date,
                                Description=text,
                                created_at=datetime.utcnow(),
                                entered_by=st.session_state.get("username", "anonymous")
                            ))
                            inserted_count += 1

            # User feedback
            if inserted_count > 0:
                st.success(f"{inserted_count} accomplishments submitted successfully!")
            if duplicates_found:
                st.warning(f"{len(duplicates_found)} duplicate accomplishments were skipped:\n- " +
                           "\n- ".join(duplicates_found))

            with st.expander("View Submitted Data"):
                st.dataframe(df)

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
