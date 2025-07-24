import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, MetaData, Table, select, insert, func
from datetime import date, timedelta

#############################
# --- Database Connection ---
#############################
DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/Iberia_BackOffice"
engine = create_engine(DATABASE_URL)
metadata = MetaData()
metadata.reflect(bind=engine)

# Reference tables
employees = metadata.tables["employees"]
workstreams = metadata.tables["workstreams"]
weekly_reports = metadata.tables["weeklyreports"]
accomplishments = metadata.tables["accomplishments"]

#######################
# Mapping Dictionaries
#######################
# --- User-friendly to DB column mapping dictionaries ---

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
    "Contractor (Last, First Name)": "name",  # For employee lookup
    "Reporting Week (MM/DD/YYYY)": "reporting_week",
    "Workstream": "workstream_name",
    "Accomplishment 1": "accomplishment_1",
    "Accomplishment 2": "accomplishment_2",
    "Accomplishment 3": "accomplishment_3",
    "Accomplishment 4": "accomplishment_4",
    "Accomplishment 5": "accomplishment_5"
}

# Columns for UI display (user-friendly)
weekly_report_columns = list(weekly_report_col_map.keys())
accomplishments_columns = list(accomplishments_col_map.keys())

# --- Helper: get most recent Monday string ---
def get_most_recent_monday():
    today = date.today()
    return today - timedelta(days=today.weekday())

most_recent_monday_str = get_most_recent_monday().strftime("%m/%d/%Y")

# --- Streamlit UI ---
st.set_page_config(page_title="Team Performance Tracker", layout="wide")
st.title("📊 Team Performance Tracker")

st.markdown("### Weekly Reports Input — Use Tab to move between cells.")
weekly_default = pd.DataFrame([{col: "" for col in weekly_report_columns}])
weekly_default.at[0, "Reporting Week (MM/DD/YYYY)"] = most_recent_monday_str

weekly_df = st.data_editor(
    weekly_default,
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
            # Rename user-friendly headers to DB column names
            cleaned_df = cleaned_df.rename(columns=weekly_report_col_map)

            # Convert dates & fix NaT -> None
            cleaned_df["weekstartdate"] = pd.to_datetime(cleaned_df["weekstartdate"], errors="coerce")
            cleaned_df["weekstartdate"] = cleaned_df["weekstartdate"].where(cleaned_df["weekstartdate"].notna(), None)

            cleaned_df["datecompleted"] = pd.to_datetime(cleaned_df["datecompleted"], errors="coerce")
            cleaned_df["datecompleted"] = cleaned_df["datecompleted"].where(cleaned_df["datecompleted"].notna(), None)

            # Convert hoursworked to numeric, fill NaNs with 0
            cleaned_df["hoursworked"] = pd.to_numeric(cleaned_df["hoursworked"], errors="coerce").fillna(0)

            # Calculate effortpercentage = (hoursworked / 40) * 100
            cleaned_df["effortpercentage"] = (cleaned_df["hoursworked"] / 40) * 100

            # Insert into DB
            with engine.begin() as conn:
                # Insert rows into weekly_reports
                rows = cleaned_df.to_dict("records")
                conn.execute(insert(weekly_reports), rows)

            st.success("✅ Weekly Reports submitted successfully!")
            st.dataframe(cleaned_df)

        except Exception as e:
            st.error(f"❌ Error inserting weekly reports: {e}")

st.markdown("---")
st.markdown("### Accomplishments Input — Use Tab to move between cells.")
accom_default = pd.DataFrame([{col: "" for col in accomplishments_columns}])
accom_default.at[0, "Reporting Week (MM/DD/YYYY)"] = most_recent_monday_str

accom_df = st.data_editor(
    accom_default,
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
            # Rename user-friendly headers to internal column names for processing
            df = cleaned_accom_df.rename(columns=accomplishments_col_map)

            with engine.begin() as conn:
                for _, row in df.iterrows():
                    contractor_name = row["name"].strip()
                    if not contractor_name:
                        st.warning("Skipping row with empty Contractor name.")
                        continue

                    # Employee lookup or insert
                    emp = conn.execute(
                        select(employees).where(func.lower(employees.c.name) == contractor_name.lower())
                    ).fetchone()
                    if emp:
                        employee_id = emp[0]
                    else:
                        employee_id = conn.execute(
                            insert(employees).values(name=contractor_name).returning(employees.c.employeeid)
                        ).scalar_one()

                    # Workstream lookup or insert
                    workstream_name = row.get("workstream_name", "").strip()
                    if workstream_name:
                        ws = conn.execute(
                            select(workstreams).where(func.lower(workstreams.c.name) == workstream_name.lower())
                        ).fetchone()
                        if ws:
                            workstream_id = ws[0]
                        else:
                            workstream_id = conn.execute(
                                insert(workstreams).values(name=workstream_name).returning(workstreams.c.workstreamid)
                            ).scalar_one()
                    else:
                        workstream_id = None

                    # Reporting week as string for daterange
                    reporting_week_str = row.get("reporting_week", "")
                    try:
                        reporting_week_str = pd.to_datetime(reporting_week_str).strftime("%m/%d/%Y")
                    except Exception:
                        reporting_week_str = str(reporting_week_str)

                    # Insert each non-empty accomplishment separately
                    for i in range(1, 6):
                        text = row.get(f"accomplishment_{i}", "").strip()
                        if text:
                            conn.execute(
                                insert(accomplishments).values(
                                    employeeid=employee_id,
                                    workstreamid=workstream_id,
                                    daterange=reporting_week_str,
                                    description=text
                                )
                            )

            st.success("✅ Accomplishments submitted successfully!")
            st.dataframe(df)

        except Exception as e:
            st.error(f"❌ Error inserting accomplishments: {e}")
