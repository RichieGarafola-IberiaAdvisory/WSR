# import streamlit as st
# from sqlalchemy import create_engine, MetaData, Table, select, insert, func
# from datetime import date

# DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/Iberia_BackOffice"
# engine = create_engine(DATABASE_URL)
# metadata = MetaData()
# metadata.reflect(bind=engine)

# employees = metadata.tables['employees']
# weekly_reports = metadata.tables['weeklyreports']
# workstreams = metadata.tables['workstreams']
# accomplishments = metadata.tables['accomplishments']
# hourstracking = metadata.tables['hourstracking']

# st.title("Submit Weekly Report and Accomplishments")

# with st.form("report_form"):
#     labor_category = st.text_input("Labor Category")
#     vendor_name = st.text_input("Vendor Name")
#     reporting_week = st.date_input("Reporting Week", value=date.today())
#     division_command = st.text_input("Division/Command")
#     work_product_title = st.text_input("Work Product Title")
#     contribution_desc = st.text_area("Brief description of individual's contribution")
#     work_product_status = st.selectbox("Work Product Status", ["In Progress", "Completed", "On Hold"])
#     planned_unplanned = st.selectbox("Planned or Unplanned (Monthly PMR)", ["Planned", "Unplanned"])
#     # date_completed = st.date_input("If Completed, Date Completed (Optional)", value=reporting_week if work_product_status == "Completed" else reporting_week)
    
#     date_completed_str = st.text_input("If Completed, Date Completed (Optional)", placeholder="YYYY-MM-DD")
#     try:
#         date_completed = datetime.strptime(date_completed_str, "%Y-%m-%d").date() if date_completed_str else None
#     except ValueError:
#         st.error("Please enter the date in YYYY-MM-DD format.")
#         date_completed = None
        
#     distinct_nfr = st.text_input("Distinct NFR")
#     distinct_cap = st.text_input("Distinct CAP")
#     hours_worked = st.number_input("Hours Worked", min_value=0.0, max_value=40.0, step=0.5, format="%.2f")
#     level_of_effort = (hours_worked / 40) * 100
#     contractor_name = st.text_input("Contractor (Last Name, First Name)")
#     govt_ta_name = st.text_input("Govt TA (Last Name, First Name)")
#     workstream_name = st.text_input("Workstream Name*")
#     date_range = st.text_input("Date Range for Accomplishments")
#     accomplishment_1 = st.text_area("Accomplishment 1")
#     accomplishment_2 = st.text_area("Accomplishment 2")
#     accomplishment_3 = st.text_area("Accomplishment 3")
#     accomplishment_4 = st.text_area("Accomplishment 4")
#     accomplishment_5 = st.text_area("Accomplishment 5")

#     submitted = st.form_submit_button("Submit")

#     if submitted:
#         with engine.begin() as conn:
#             result = conn.execute(
#                 select(employees).where(func.lower(employees.c.name) == contractor_name.lower())
#             ).fetchone()
#             if result:
#                 employee_id = result[0]
#             else:
#                 employee_id = conn.execute(
#                     insert(employees)
#                     .values(name=contractor_name, laborcategory=labor_category, vendorname=vendor_name)
#                     .returning(employees.c.employeeid)
#                 ).scalar_one()

#             ws_result = conn.execute(
#                 select(workstreams).where(workstreams.c.name == workstream_name)
#             ).mappings().fetchone()
#             if ws_result:
#                 workstream_id = ws_result['workstreamid']
#             else:
#                 ws_result = conn.execute(
#                     insert(workstreams)
#                     .values(name=workstream_name, description="")
#                     .returning(workstreams.c.workstreamid)
#                 ).fetchone()
#                 workstream_id = ws_result[0]



#             conn.execute(
#                 insert(weekly_reports).values(
#                     employeeid=employee_id,
#                     weekstartdate=reporting_week,
#                     divisioncommand=division_command,
#                     workproducttitle=work_product_title,
#                     contributiondescription=contribution_desc,
#                     status=work_product_status,
#                     plannedorunplanned=planned_unplanned,
#                     datecompleted=date_completed if work_product_status == "Completed" else None,
#                     distinctnfr=distinct_nfr,
#                     distinctcap=distinct_cap,
#                     effortpercentage=level_of_effort,
#                     contractorname=contractor_name,
#                     govttaname=govt_ta_name
#                 )
#             )
            
#             conn.execute(
#             insert(hourstracking).values(
#                 employeeid=employee_id,
#                 workstreamid=workstream_id,
#                 reportingweek=reporting_week,
#                 hoursworked=hours_worked,
#                 levelofeffort=level_of_effort
#             )
#         )


#             for text in [accomplishment_1, accomplishment_2, accomplishment_3, accomplishment_4, accomplishment_5]:
#                 if text.strip():
#                     conn.execute(
#                         insert(accomplishments).values(
#                             employeeid=employee_id,
#                             workstreamid=workstream_id,
#                             daterange=date_range,
#                             description=text.strip()
#                         )
#                     )

#         st.success("Report and accomplishments submitted directly to PostgreSQL successfully!")







import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, MetaData, Table, insert
from datetime import date, timedelta

# --- Database Connection ---
DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/Iberia_BackOffice"
engine = create_engine(DATABASE_URL)
metadata = MetaData()
metadata.reflect(bind=engine)

# Reference the table you're inserting into
weekly_reports = metadata.tables["weeklyreports"]

# --- Mapping user-friendly column names to DB column names ---
user_to_db_col_map = {
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

# --- Streamlit UI ---
st.set_page_config(page_title="Team Performance Tracker", layout="wide")
st.title("📊 Team Performance Tracker")
st.markdown("Enter your team’s weekly contributions below. Use Tab to move between cells.")

# Use user-friendly headers for UI
columns = list(user_to_db_col_map.keys())

# Get most recent Monday
today = date.today()
most_recent_monday = today - timedelta(days=today.weekday())  # Monday=0
monday_str = most_recent_monday.strftime("%m/%d/%Y")

# Create one blank row with the date filled in
default_data = pd.DataFrame([{col: "" for col in columns}])
default_data.at[0, "Reporting Week (MM/DD/YYYY)"] = monday_str

# Editable grid (Excel-style)
edited_df = st.data_editor(
    default_data,
    use_container_width=True,
    hide_index=True,
    num_rows="dynamic"
)

# Submission section
if st.button("✅ Submit Weekly Report"):
    cleaned_df = edited_df.dropna(how="all")
    if cleaned_df.empty:
        st.warning("⚠️ Please fill in at least one row before submitting.")
    else:
        try:
            # Rename columns to DB column names
            cleaned_df.rename(columns=user_to_db_col_map, inplace=True)

            # Convert date columns to datetime
            cleaned_df["weekstartdate"] = pd.to_datetime(cleaned_df["weekstartdate"], errors="coerce")
            cleaned_df["weekstartdate"] = cleaned_df["weekstartdate"].where(cleaned_df["weekstartdate"].notna(), None)

            cleaned_df["datecompleted"] = pd.to_datetime(cleaned_df["datecompleted"], errors="coerce")
            cleaned_df["datecompleted"] = cleaned_df["datecompleted"].where(cleaned_df["datecompleted"].notna(), None)


            # Convert hoursworked to numeric, fill NaN with 0
            cleaned_df["hoursworked"] = pd.to_numeric(cleaned_df["hoursworked"], errors="coerce").fillna(0)

            # Calculate effortpercentage (optional if you store it)
            cleaned_df["effortpercentage"] = (cleaned_df["hoursworked"] / 40) * 100

            # Drop any columns not in DB schema (e.g. effortpercentage if not in your DB)
            # If effortpercentage is in DB, keep it; else remove before insert
            if "effortpercentage" not in weekly_reports.columns:
                cleaned_df.drop(columns=["effortpercentage"], inplace=True, errors="ignore")

            # Convert DataFrame to list of dicts for insertion
            rows_to_insert = cleaned_df.to_dict("records")

            # Insert into DB inside a transaction
            with engine.begin() as conn:
                conn.execute(insert(weekly_reports), rows_to_insert)

            st.success("✅ Data successfully submitted to the database!")
            st.dataframe(cleaned_df)

        except Exception as e:
            st.error(f"❌ Error inserting into database: {e}")
