import streamlit as st
from sqlalchemy import create_engine, MetaData, Table, select, insert, func
from datetime import date

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

with st.form("report_form"):
    labor_category = st.text_input("Labor Category")
    vendor_name = st.text_input("Vendor Name")
    reporting_week = st.date_input("Reporting Week", value=date.today())
    division_command = st.text_input("Division/Command")
    work_product_title = st.text_input("Work Product Title")
    contribution_desc = st.text_area("Brief description of individual's contribution")
    work_product_status = st.selectbox("Work Product Status", ["In Progress", "Completed", "On Hold"])
    planned_unplanned = st.selectbox("Planned or Unplanned (Monthly PMR)", ["Planned", "Unplanned"])
    # date_completed = st.date_input("If Completed, Date Completed (Optional)", value=reporting_week if work_product_status == "Completed" else reporting_week)
    
    date_completed_str = st.text_input("If Completed, Date Completed (Optional)", placeholder="YYYY-MM-DD")
    try:
        date_completed = datetime.strptime(date_completed_str, "%Y-%m-%d").date() if date_completed_str else None
    except ValueError:
        st.error("Please enter the date in YYYY-MM-DD format.")
        date_completed = None
        
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