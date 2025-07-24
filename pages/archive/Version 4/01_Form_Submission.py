# Import required libraries
import streamlit as st  # Used to build the interactive web app
import pandas as pd  # Used for working with tabular data
from sqlalchemy import create_engine, MetaData, Table, select, insert, func  # For database operations
from datetime import date, timedelta  # For working with dates

####################
# --- Page Configuration ---
####################
# Configure the layout of the Streamlit page
st.set_page_config(
    # browser tab title
    page_title="Weekly Form Submission", 
    # wide layout for more screen space
    layout="wide")

# Display logo at top of app (ensure image path points to valid directory)
st.image("images/Iberia-Advisory.png", width=250)

####################################
# --- Page Title and Description ---
####################################
# Display the main title and a short description below it
st.title("Weekly Form Submission Portal")
st.caption("Log your team's contributions and accomplishments for the week.")

####################
# --- DB Setup ---
####################
# Connect to the PostgreSQL database
DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/Iberia_BackOffice"
engine = create_engine(DATABASE_URL)

# Reflect tables from the existing database schema
metadata = MetaData()
metadata.reflect(bind=engine)

# Define references to the database tables
employees = metadata.tables["employees"]
workstreams = metadata.tables["workstreams"]
weekly_reports = metadata.tables["weeklyreports"]
accomplishments = metadata.tables["accomplishments"]
hourstracking = metadata.tables["hourstracking"]

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
weekly_report_columns = list(weekly_report_col_map.keys())
accomplishments_columns = list(accomplishments_col_map.keys())

#########################
# --- Helper Function ---
#########################
# Return the most recent Monday (used as default week start)
def get_most_recent_monday():
    today = date.today()
    return today - timedelta(days=today.weekday())

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
weekly_default = pd.DataFrame([{col: "" for col in weekly_report_columns}])
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
            cleaned_df["weekstartdate"] = cleaned_df["weekstartdate"].apply(lambda x: x if pd.notnull(x) else None)
            cleaned_df["datecompleted"] = cleaned_df["datecompleted"].apply(lambda x: x if pd.notnull(x) else None)
            cleaned_df["hoursworked"] = pd.to_numeric(cleaned_df["hoursworked"], errors="coerce").fillna(0)
            cleaned_df["effortpercentage"] = (cleaned_df["hoursworked"] / 40) * 100

            # Begin database transaction
            with engine.begin() as conn:
                for _, row in cleaned_df.iterrows():
                    contractor = row["contractorname"].strip()
                    if not contractor:
                        continue

                    # Check if contractor exists; if not, insert into Employees
                    emp = conn.execute(
                        select(employees).where(func.lower(employees.c.name) == contractor.lower())
                    ).fetchone()
                    employee_id = emp[0] if emp else conn.execute(
                        insert(employees).values(
                            name=contractor,
                            laborcategory=row.get("laborcategory"),
                            vendorname=row.get("vendorname")
                        ).returning(employees.c.employeeid)
                    ).scalar_one()

                    # Insert Weekly Report
                    conn.execute(
                        insert(weekly_reports).values(
                            employeeid=employee_id,
                            weekstartdate=row["weekstartdate"],
                            divisioncommand=row["divisioncommand"],
                            workproducttitle=row["workproducttitle"],
                            contributiondescription=row["contributiondescription"],
                            status=row["status"],
                            plannedorunplanned=row["plannedorunplanned"],
                            datecompleted=row["datecompleted"],
                            distinctnfr=row["distinctnfr"],
                            distinctcap=row["distinctcap"],
                            effortpercentage=row["effortpercentage"],
                            contractorname=contractor,
                            govttaname=row["govttaname"]
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
                                levelofeffort=row["effortpercentage"]
                            )
                        )

            st.success("Weekly Reports submitted successfully!")
            # Show the submitted data
            with st.expander("View Submitted Data"):
                st.dataframe(cleaned_df)

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
accom_default = pd.DataFrame([{col: "" for col in accomplishments_columns}])
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
if st.button("Submit Accomplishments"):
    cleaned_accom_df = accom_df.dropna(how="all")
    if cleaned_accom_df.empty:
        st.warning("Please fill at least one row of accomplishments.")
    else:
        try:
            df = cleaned_accom_df.rename(columns=accomplishments_col_map)
            
            # Start DB transaction
            with engine.begin() as conn:
                for _, row in df.iterrows():
                    contractor = row["name"].strip()
                    if not contractor:
                        continue

                    # Get or insert employee
                    emp = conn.execute(
                        select(employees).where(func.lower(employees.c.name) == contractor.lower())
                    ).fetchone()
                    employee_id = emp[0] if emp else conn.execute(
                        insert(employees).values(name=contractor).returning(employees.c.employeeid)
                    ).scalar_one()

                    # Get or insert workstream
                    workstream_name = row.get("workstream_name", "").strip()
                    workstream_id = None
                    if workstream_name:
                        ws = conn.execute(
                            select(workstreams).where(func.lower(workstreams.c.name) == workstream_name.lower())
                        ).fetchone()
                        workstream_id = ws[0] if ws else conn.execute(
                            insert(workstreams).values(name=workstream_name).returning(workstreams.c.workstreamid)
                        ).scalar_one()

                    # Convert date to string
                    date_range = row.get("reporting_week")
                    date_range_str = date_range.strftime("%m/%d/%Y") if pd.notnull(date_range) else ""

                    # Insert each accomplishment (up to 5 per row)
                    for i in range(1, 6):
                        text = row.get(f"accomplishment_{i}", "").strip()
                        if text:
                            conn.execute(
                                insert(accomplishments).values(
                                    employeeid=employee_id,
                                    workstreamid=workstream_id,
                                    daterange=date_range_str,
                                    description=text
                                )
                            )

            st.success("Accomplishments submitted successfully!")
            # Show submitted data
            with st.expander("View Submitted Data"):
                st.dataframe(df)

        except Exception as e:
            st.error(f"❌ Error inserting accomplishments: {e}")
            
            
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
