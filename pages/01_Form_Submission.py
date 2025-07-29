import streamlit as st
import pandas as pd
from sqlalchemy import insert
from datetime import datetime

# Import only functions
from utils.db import get_engine, load_tables
from utils.helpers import (
    get_most_recent_monday,
    get_or_create_employee,
    get_or_create_workstream,
    clean_dataframe_dates_hours,
    normalize_text
)

# ----------------------------
# Page Setup
# ----------------------------
st.set_page_config(page_title="Weekly Form Submission", layout="wide")
st.image("images/Iberia-Advisory.png", width=250)
st.title("Weekly Form Submission Portal")
st.caption("Log your team's contributions and accomplishments for the week.")

# ----------------------------
# Lazy-load tables
# ----------------------------
load_tables()
from utils import db
employees = db.employees
weekly_reports = db.weekly_reports
hourstracking = db.hourstracking
accomplishments = db.accomplishments

# ----------------------------
# Column Maps
# ----------------------------
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

weekly_columns = list(weekly_report_col_map.keys())
accom_columns = list(accomplishments_col_map.keys())
most_recent_monday = get_most_recent_monday()

# ----------------------------
# Weekly Reports Section
# ----------------------------
st.markdown("## Weekly Reports")
with st.expander("Instructions", expanded=False):
    st.markdown("""
    - Use **Tab** to move across fields quickly.
    - Enter actual hours worked (up to 40).
    - Leave blank rows empty — they'll be ignored.
    """)

weekly_default = pd.DataFrame([{col: "" for col in weekly_columns}])
weekly_default.at[0, "Reporting Week (MM/DD/YYYY)"] = most_recent_monday
weekly_default.at[0, "If Completed (YYYY-MM-DD)"] = pd.NaT

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

if st.button("Submit Weekly Reports"):
    cleaned_df = weekly_df.dropna(how="all")
    if cleaned_df.empty:
        st.warning("Please fill at least one row before submitting.")
    else:
        try:
            cleaned_df = cleaned_df.rename(columns=weekly_report_col_map)
            cleaned_df = clean_dataframe_dates_hours(cleaned_df, 
                                                     date_cols=["weekstartdate", "datecompleted"],
                                                     numeric_cols=["hoursworked"])
            cleaned_df["effortpercentage"] = (cleaned_df["hoursworked"] / 40) * 100

            with get_engine().begin() as conn:
                weekly_data = []
                hours_data = []

                for _, row in cleaned_df.iterrows():
                    contractor = normalize_text(row.get("contractorname", ""))
                    if not contractor:
                        continue

                    employee_id = get_or_create_employee(
                        conn,
                        contractor_name=contractor,
                        vendor=normalize_text(row.get("vendorname", "")),
                        laborcategory=normalize_text(row.get("laborcategory", ""))
                    )

                    weekly_data.append({
                        "EmployeeID": employee_id,
                        "WeekStartDate": row["weekstartdate"],
                        "DivisionCommand": normalize_text(row.get("divisioncommand", "")),
                        "WorkProductTitle": normalize_text(row.get("workproducttitle", "")),
                        "ContributionDescription": normalize_text(row.get("contributiondescription", "")),
                        "Status": normalize_text(row.get("status", "")),
                        "PlannedOrUnplanned": row.get("plannedorunplanned", "").strip().lower(),
                        "DateCompleted": row["datecompleted"],
                        "DistinctNFR": normalize_text(row.get("distinctnfr", "")),
                        "DistinctCAP": normalize_text(row.get("distinctcap", "")),
                        "EffortPercentage": row["effortpercentage"],
                        "ContractorName": contractor,
                        "GovtTAName": normalize_text(row.get("govttaname", "")),
                    })

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

            st.success("Weekly Reports submitted successfully!")
            with st.expander("View Submitted Data"):
                st.dataframe(cleaned_df)

        except Exception as e:
            st.error(f"Error inserting weekly reports: {e}")

# ----------------------------
# Accomplishments Section
# ----------------------------
st.markdown("---")
st.markdown("## Weekly Accomplishments")
with st.expander("Instructions", expanded=False):
    st.markdown("""
    - Each row represents one contractor's accomplishments for the week.
    - Up to 5 accomplishments per person.
    - Leave unused fields blank.
    """)

accom_default = pd.DataFrame([{col: "" for col in accom_columns}])
accom_default.at[0, "Reporting Week (MM/DD/YYYY)"] = most_recent_monday

accom_df = st.data_editor(
    accom_default,
    column_config={
        "Reporting Week (MM/DD/YYYY)": st.column_config.DateColumn("Reporting Week"),
    },
    use_container_width=True,
    hide_index=True,
    num_rows="dynamic"
)

if st.button("Submit Accomplishments"):
    cleaned_accom_df = accom_df.dropna(how="all")
    if cleaned_accom_df.empty:
        st.warning("Please fill at least one row of accomplishments.")
    else:
        try:
            df = cleaned_accom_df.rename(columns=accomplishments_col_map)
            with get_engine().begin() as conn:
                accomplishment_data = []

                for _, row in df.iterrows():
                    contractor = normalize_text(row.get("name", ""))
                    if not contractor:
                        continue

                    employee_id = get_or_create_employee(conn, contractor)
                    workstream_id = get_or_create_workstream(conn, normalize_text(row.get("workstream_name", "")))

                    reporting_week = row.get("reporting_week")
                    week_date = (
                        pd.to_datetime(reporting_week, errors="coerce").date()
                        if pd.notnull(reporting_week)
                        else None
                    )

                    for i in range(1, 6):
                        text = normalize_text(row.get(f"accomplishment_{i}", ""))
                        if text:
                            accomplishment_data.append({
                                "EmployeeID": employee_id,
                                "WorkstreamID": workstream_id,
                                "DateRange": week_date,
                                "Description": text,
                            })

                if accomplishment_data:
                    conn.execute(insert(accomplishments), accomplishment_data)

            st.success("Accomplishments submitted successfully!")
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
