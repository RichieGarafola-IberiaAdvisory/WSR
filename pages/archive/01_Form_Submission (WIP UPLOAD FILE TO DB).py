import streamlit as st
from sqlalchemy import create_engine, MetaData, Table, select, insert, func
from datetime import date
import pandas as pd

DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/Iberia_BackOffice"
engine = create_engine(DATABASE_URL)
metadata = MetaData()
metadata.reflect(bind=engine)

employees = metadata.tables['employees']
weekly_reports = metadata.tables['weeklyreports']
workstreams = metadata.tables['workstreams']
accomplishments = metadata.tables['accomplishments']
hourstracking = metadata.tables['hourstracking']

st.title("Submit Weekly Report and Accomplishments")

st.sidebar.subheader("Upload WSR Report File")
uploaded_file = st.sidebar.file_uploader("Upload CSV or Excel", type=["csv", "xlsx"])

if uploaded_file:
    # Read CSV or Excel
    if uploaded_file.type == "text/csv":
        uploaded_df = pd.read_csv(uploaded_file)
    else:
        uploaded_df = pd.read_excel(uploaded_file)

    # Clean up column names
    uploaded_df.columns = (
        uploaded_df.columns
        .str.strip()
        .str.lower()
        .str.replace(" ", "_")
        .str.replace("'", "")
        .str.replace(",", "")
        .str.replace(r"[^a-z0-9_]", "", regex=True)  # Remove all non-alphanumeric/underscore chars including slashes
    )


    st.sidebar.success(f"Loaded {len(uploaded_df)} rows from file")
    st.sidebar.dataframe(uploaded_df.head())
    st.write("Columns in uploaded file:", uploaded_df.columns.tolist())  # Optional for debug

    if st.sidebar.button("Insert uploaded data to DB"):
        with engine.begin() as conn:
            inserted_count = 0
            skipped_count = 0

            for _, row in uploaded_df.iterrows():
                contractor_name_row = row.get("contractor_last_name_first_name")
                if not contractor_name_row or str(contractor_name_row).strip() == "":
                    skipped_count += 1
                    continue
                contractor_name_row = str(contractor_name_row).strip()

                labor_category_row = row.get("labor_category") or ""
                vendor_name_row = row.get("vendor_name") or ""
                workstream_name_row = row.get("workstream_name") or ""

                reporting_week_row = row.get("reporting_week_mm_dd_yyyy")
                if pd.isna(reporting_week_row):
                    reporting_week_row = pd.to_datetime("today").date()
                else:
                    try:
                        reporting_week_row = pd.to_datetime(reporting_week_row).date()
                    except Exception:
                        reporting_week_row = pd.to_datetime("today").date()

                # Lookup or insert employee
                result = conn.execute(
                    select(employees).where(func.lower(employees.c.name) == contractor_name_row.lower())
                ).fetchone()

                if result:
                    employee_id = result[0]
                else:
                    employee_id = conn.execute(
                        insert(employees)
                        .values(name=contractor_name_row, laborcategory=labor_category_row, vendorname=vendor_name_row)
                        .returning(employees.c.employeeid)
                    ).scalar_one()

                # Lookup or insert workstream
                ws_result = conn.execute(
                    select(workstreams).where(workstreams.c.name == workstream_name_row)
                ).mappings().fetchone()

                if ws_result:
                    workstream_id = ws_result['workstreamid']
                else:
                    ws_result = conn.execute(
                        insert(workstreams)
                        .values(name=workstream_name_row, description="")
                        .returning(workstreams.c.workstreamid)
                    ).fetchone()
                    workstream_id = ws_result[0]
                    
                datecompleted_val = row.get("If Completed") or row.get("datecompleted")
                if pd.isna(datecompleted_val) or datecompleted_val in ["NaN", "", None]:
                    datecompleted_val = None
                else:
                    try:
                        datecompleted_val = pd.to_datetime(datecompleted_val).date()
                    except Exception:
                        datecompleted_val = None


                # Insert weekly report
                conn.execute(
                    insert(weekly_reports).values(
                        employeeid=employee_id,
                        weekstartdate=reporting_week_row,
                        divisioncommand=row.get("Division/Command") or row.get("divisioncommand"),
                        workproducttitle=row.get("Work Product Title") or row.get("workproducttitle"),
                        contributiondescription=row.get("Brief description of individual's contribution") or row.get("contributiondescription"),
                        status=row.get("Work Product Status") or row.get("status"),
                        plannedorunplanned=row.get("Planned or Unplanned (Monthly PMR)") or row.get("plannedorunplanned"),
                        datecompleted=datecompleted_val,
                        distinctnfr=row.get("Distinct NFR ") or row.get("distinctnfr"),
                        distinctcap=row.get("Distinct CAP ") or row.get("distinctcap"),
                        effortpercentage=row.get("Time Spent (Hours)") or row.get("effortpercentage"),
                        contractorname=contractor_name_row,
                        govttaname=row.get("Govt TA") or row.get("govttaname"),
                    )
                )


                # Insert hours tracking
                conn.execute(
                    insert(hourstracking).values(
                        employeeid=employee_id,
                        workstreamid=workstream_id,
                        reportingweek=reporting_week_row,
                        hoursworked=row.get("time_spent_hours") or 0,
                        levelofeffort=row.get("time_spent_hours") or 0,
                    )
                )

                inserted_count += 1

        st.sidebar.success(f"Inserted {inserted_count} rows into the database!")
        if skipped_count > 0:
            st.sidebar.warning(f"Skipped {skipped_count} rows due to missing Contractor Name.")

            

with st.form("report_form"):
    labor_category = st.text_input("Labor Category")
    vendor_name = st.text_input("Vendor Name")
    reporting_week = st.date_input("Reporting Week", value=date.today())
    division_command = st.text_input("Division/Command")
    work_product_title = st.text_input("Work Product Title")
    contribution_desc = st.text_area("Brief description of individual's contribution")
    work_product_status = st.selectbox("Work Product Status", ["In Progress", "Completed", "On Hold"])
    planned_unplanned = st.selectbox("Planned or Unplanned (Monthly PMR)", ["Planned", "Unplanned"])
    date_completed = st.date_input("If Completed, Date Completed (Optional)", value=reporting_week if work_product_status == "Completed" else reporting_week)
    distinct_nfr = st.text_input("Distinct NFR")
    distinct_cap = st.text_input("Distinct CAP")
    hours_worked = st.number_input("Hours Worked", min_value=0.0, max_value=40.0, step=0.5, format="%.2f")
    level_of_effort = (hours_worked / 40) * 100
    contractor_name = st.text_input("Contractor (Last Name, First Name)")
    govt_ta_name = st.text_input("Govt TA (Last Name, First Name)")
    workstream_name = st.text_input("Workstream Name*")
    date_range = st.text_input("Date Range for Accomplishments")
    accomplishment_1 = st.text_area("Accomplishment 1")
    accomplishment_2 = st.text_area("Accomplishment 2")
    accomplishment_3 = st.text_area("Accomplishment 3")
    accomplishment_4 = st.text_area("Accomplishment 4")
    accomplishment_5 = st.text_area("Accomplishment 5")

    submitted = st.form_submit_button("Submit")

    if submitted:
        with engine.begin() as conn:
            result = conn.execute(
                select(employees).where(func.lower(employees.c.name) == contractor_name.lower())
            ).fetchone()
            if result:
                employee_id = result[0]
            else:
                employee_id = conn.execute(
                    insert(employees)
                    .values(name=contractor_name, laborcategory=labor_category, vendorname=vendor_name)
                    .returning(employees.c.employeeid)
                ).scalar_one()

            ws_result = conn.execute(
                select(workstreams).where(workstreams.c.name == workstream_name)
            ).mappings().fetchone()
            if ws_result:
                workstream_id = ws_result['workstreamid']
            else:
                ws_result = conn.execute(
                    insert(workstreams)
                    .values(name=workstream_name, description="")
                    .returning(workstreams.c.workstreamid)
                ).fetchone()
                workstream_id = ws_result[0]



            conn.execute(
                insert(weekly_reports).values(
                    employeeid=employee_id,
                    weekstartdate=reporting_week,
                    divisioncommand=division_command,
                    workproducttitle=work_product_title,
                    contributiondescription=contribution_desc,
                    status=work_product_status,
                    plannedorunplanned=planned_unplanned,
                    datecompleted=date_completed if work_product_status == "Completed" else None,
                    distinctnfr=distinct_nfr,
                    distinctcap=distinct_cap,
                    effortpercentage=level_of_effort,
                    contractorname=contractor_name,
                    govttaname=govt_ta_name
                )
            )
            
            conn.execute(
            insert(hourstracking).values(
                employeeid=employee_id,
                workstreamid=workstream_id,
                reportingweek=reporting_week,
                hoursworked=hours_worked,
                levelofeffort=level_of_effort
            )
        )


            for text in [accomplishment_1, accomplishment_2, accomplishment_3, accomplishment_4, accomplishment_5]:
                if text.strip():
                    conn.execute(
                        insert(accomplishments).values(
                            employeeid=employee_id,
                            workstreamid=workstream_id,
                            daterange=date_range,
                            description=text.strip()
                        )
                    )

        st.success("Report and accomplishments submitted directly to PostgreSQL successfully!")