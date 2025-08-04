# pages/01_Form_Submission.py

import streamlit as st
import pandas as pd
from sqlalchemy.exc import OperationalError
import sys, os
from datetime import datetime, timezone
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
    normalize_text
)

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

####################
# --- Page Setup ---
####################
st.set_page_config(page_title="Weekly Form Submission", layout="wide")
st.image("images/Iberia-Advisory.png", width=250)

st.title("Weekly Form Submission Portal")
st.caption("Each contractor must have exactly 5 accomplishments per week.")

# Load cached session data
try:
    session_data = get_session_data()
except Exception:
    st.error("⚠️ Database is currently offline. Submissions cannot be saved.")
    session_data = None

# --- Column Mapping ---
weekly_report_col_map = {
    "Reporting Week (MM/DD/YYYY)": "weekstartdate",
    "Vendor Name": "vendorname",
    "Division/Command": "divisioncommand",
    "Workstream": "workstream_name",
    "Work Product Title": "workproducttitle",
    "Work Product Status": "status",
    "Planned or Unplanned": "plannedorunplanned",
    "If Completed (YYYY-MM-DD)": "datecompleted",
    "Distinct NFR": "distinctnfr",
    "Distinct CAP": "distinctcap",
    "Time Spent Hours": "hoursworked",
    "Contractor (Last, First Name)": "contractorname",
    "Govt TA (Last, First Name)": "govttaname",
    "Labor Category": "laborcategory",
    "Accomplishment 1": "accomplishment1",
    "Accomplishment 2": "accomplishment2",
    "Accomplishment 3": "accomplishment3",
    "Accomplishment 4": "accomplishment4",
    "Accomplishment 5": "accomplishment5",
}

weekly_columns = list(weekly_report_col_map.keys())

# Default row
most_recent_monday = get_most_recent_monday()
weekly_default = pd.DataFrame([{col: "" for col in weekly_columns}])
weekly_default.at[0, "Reporting Week (MM/DD/YYYY)"] = most_recent_monday
weekly_default.at[0, "If Completed (YYYY-MM-DD)"] = pd.NaT

# Editable table
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

st.caption("ℹ️ Tip: Each contractor can submit multiple work products per week, "
           "but must have exactly 5 accomplishments total. "
           "The table below will highlight incomplete or excessive entries.")

def highlight_rows(row):
    mapped = row.rename(index=weekly_report_col_map).rename(index=str.lower)
    total_accomplishments = sum(
        pd.notna(mapped.get(f"accomplishment{i}", None)) and mapped.get(f"accomplishment{i}") != ""
        for i in range(1, 6)
    )
    
    # Green = complete, Yellow = incomplete, Red = exceeds
    if total_accomplishments == 5:
        return ['background-color: #d4edda'] * len(row)
    elif total_accomplishments > 5:
        return ['background-color: #f8d7da'] * len(row)
    else:
        return ['background-color: #fff3cd'] * len(row)

styled_df = weekly_df.style.apply(highlight_rows, axis=1)
st.dataframe(styled_df, use_container_width=True)

###############################
# Live Accomplishment Counter
###############################
def count_accomplishments(df):
    mapped = df.rename(columns=weekly_report_col_map).rename(columns=str.lower)
    grouped = (
        mapped.groupby(["contractorname", "weekstartdate"])[[f"accomplishment{i}" for i in range(1, 6)]]
        .apply(lambda g: g.notna().sum().sum())
    )
    return grouped

if not weekly_df.empty:
    counts = count_accomplishments(weekly_df)
    for (contractor, week), total in counts.items():
        if total < 5:
            st.warning(f"⚠{contractor} ({week}) has only {total}/5 accomplishments.")
        elif total > 5:
            st.error(f"{contractor} ({week}) exceeds 5 accomplishments with {total}.")
        else:
            st.info(f"{contractor} ({week}) has exactly 5 accomplishments.")


########################
# --- Retry Helper ---
########################
def with_retry(func, max_attempts=3, delay=2):
    for attempt in range(1, max_attempts + 1):
        try:
            return func()
        except OperationalError:
            if attempt < max_attempts:
                st.warning(f"Database connection lost. Retrying ({attempt}/{max_attempts})...")
                time.sleep(delay)
            else:
                raise

######################################
# --- Submit Weekly Reports Button ---
######################################
def validate_accomplishments(df):
    """
    Ensures each contractor has at least 5 accomplishments total for each week.
    """
    required_cols = {"contractorname", "weekstartdate"} | {
        f"accomplishment{i}" for i in range(1, 6)
    }
    
    # Fill any missing expected columns with None
    for col in required_cols:
        if col not in df.columns:
            df[col] = None

    grouped = (
        df.groupby(["contractorname", "weekstartdate"])[[f"accomplishment{i}" for i in range(1, 6)]]
        .apply(lambda g: g.notna().sum().sum())
        .reset_index(name="total_accomplishments")
    )

    return grouped[grouped["total_accomplishments"] != 5]


# --- Check if all contractors have exactly 5 accomplishments ---
mapped_for_validation = weekly_df.rename(columns=weekly_report_col_map).rename(columns=str.lower)
invalid_rows = validate_accomplishments(mapped_for_validation)
form_ready = invalid_rows.empty and not weekly_df.dropna(how="all").empty


if st.button("Submit Weekly Reports", key="submit_weekly", disabled=not form_ready):
    if session_data is None:
        st.warning("⚠️ Database is offline. Please try again later.")
    else:
        cleaned_df = weekly_df.dropna(how="all")
        if cleaned_df.empty:
            st.warning("Please fill at least one row before submitting.")
        else:
            # Normalize column names for validation
            mapped_cleaned = cleaned_df.rename(columns=weekly_report_col_map).rename(columns=str.lower)
            invalid = validate_accomplishments(mapped_cleaned)

            if not invalid.empty:
                st.error(
                    "🚨 Submission blocked: "
                    + "; ".join(
                        f"{row['contractorname']} (Week {row['weekstartdate']}) "
                        f"has only {row['total_accomplishments']} accomplishments"
                        for _, row in invalid.iterrows()
                    )
                    + ". Each contractor must have 5 total accomplishments."
                )
            else:
                try:
                    def insert_weekly():
                        # Filter only columns that exist in both DataFrame and mapping
                        valid_cols = [col for col in cleaned_df.columns if col in weekly_report_col_map]
                        df = cleaned_df[valid_cols].rename(columns=weekly_report_col_map)
                    
                        # Ensure all required mapped columns exist even if missing
                        for mapped_col in weekly_report_col_map.values():
                            if mapped_col not in df.columns:
                                df[mapped_col] = None
                    
                        df = clean_dataframe_dates_hours(
                            df,
                            date_cols=["weekstartdate", "datecompleted"],
                            numeric_cols=["hoursworked"]
                        )

                        df["effortpercentage"] = (df["hoursworked"] / 40) * 100

                        with get_engine().begin() as conn:
                            weekly_data, hours_data, employee_cache, workstream_cache = [], [], {}, {}
                            duplicates_found, inserted_count = [], 0
                            existing = get_data("WeeklyReports")

                            for (contractor, week), group in df.groupby(["contractorname", "weekstartdate"]):
                                if contractor not in employee_cache:
                                    employee_cache[contractor] = get_or_create_employee(
                                        contractor_name=contractor,
                                        vendor=normalize_text(group["vendorname"].iloc[0]),
                                        laborcategory=normalize_text(group["laborcategory"].iloc[0])
                                    )
                                employee_id = employee_cache[contractor]

                                # Workstream handling (same for the entire group)
                                workstream_name = normalize_text(group["workstream_name"].iloc[0])
                                if workstream_name not in workstream_cache:
                                    workstream_cache[workstream_name] = get_or_create_workstream(
                                        conn=conn,
                                        workstream_name=workstream_name
                                    )
                                workstream_id = workstream_cache[workstream_name]

                                # Combine accomplishments
                                all_accomplishments = []
                                for _, row in group.iterrows():
                                    for i in range(1, 6):
                                        val = normalize_text(row.get(f"accomplishment{i}", ""))
                                        if val:
                                            all_accomplishments.append(val)

                                contribution_description = "; ".join(all_accomplishments)
                                
                                for _, row in group.iterrows():
                                    duplicate_check = existing[
                                        (existing["EmployeeID"] == employee_id) &
                                        (existing["WeekStartDate"] == week) &
                                        (existing["WorkProductTitle"] == normalize_text(row.get("workproducttitle", "")))
                                    ]
                                    if not duplicate_check.empty:
                                        duplicates_found.append(row.get("workproducttitle"))
                                        continue

                                    weekly_data.append({
                                        "EmployeeID": employee_id,
                                        "WorkstreamID": workstream_id, 
                                        "WeekStartDate": week,
                                        "DivisionCommand": normalize_text(row.get("divisioncommand", "")),
                                        "WorkProductTitle": normalize_text(row.get("workproducttitle", "")),
                                        "ContributionDescription": contribution_description,
                                        "Status": normalize_text(row.get("status", "")),
                                        "PlannedOrUnplanned": normalize_text(row.get("plannedorunplanned", "")),
                                        "DateCompleted": row["datecompleted"],
                                        "DistinctNFR": normalize_text(row.get("distinctnfr", "")),
                                        "DistinctCAP": normalize_text(row.get("distinctcap", "")),
                                        "EffortPercentage": row["effortpercentage"],
                                        "ContractorName": contractor,
                                        "GovtTAName": normalize_text(row.get("govttaname", "")),
                                        "Accomplishment1": row.get("accomplishment1", ""),
                                        "Accomplishment2": row.get("accomplishment2", ""),
                                        "Accomplishment3": row.get("accomplishment3", ""),
                                        "Accomplishment4": row.get("accomplishment4", ""),
                                        "Accomplishment5": row.get("accomplishment5", ""),
                                    })
                                    inserted_count += 1

                                    if row["hoursworked"] > 0:
                                        hours_data.append({
                                            "EmployeeID": employee_id,
                                            "WorkstreamID": workstream_id,
                                            "ReportingWeek": week,
                                            "HoursWorked": row["hoursworked"],
                                            "LevelOfEffort": row["effortpercentage"],
                                        })

                            for row in weekly_data:
                                insert_row("WeeklyReports", {
                                    **row,
                                    "CreatedAt": datetime.now(timezone.utc),
                                    "EnteredBy": "anonymous"
                                })
                            for row in hours_data:
                                insert_row("HoursTracking", {
                                    **row,
                                    "CreatedAt": datetime.now(timezone.utc),
                                    "EnteredBy": "anonymous"
                                })

                        msg = f"Weekly Reports submitted: {inserted_count}."
                        if duplicates_found:
                            msg += f" Skipped {len(duplicates_found)} duplicates."
                        st.success(msg)
                        session_data = get_session_data()

                    with_retry(insert_weekly)
                    st.success("Weekly Reports submitted successfully!")
                    session_data = get_session_data()
                    st.session_state["weekly_df"] = pd.DataFrame([{col: "" for col in weekly_columns}])
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
