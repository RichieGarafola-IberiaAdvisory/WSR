import streamlit as st
from sqlalchemy import create_engine
import pandas as pd
import os
import re
import requests
from ms_auth import get_token


st.title("Submit Weekly Report")

# Database URL
database_url = "postgresql://postgres:postgres@localhost:5432/Iberia_BackOffice"

# Create Engine
engine = create_engine(database_url)

def inset_submission_to_db(data: dict):
    df = pd.DataFrame([data])
    try:
        df.to_sql("WSR

def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    import re
    df.columns = [re.sub(r'\s+', ' ', str(col)).replace("*", "").strip() for col in df.columns]
   
    rename_map = {}
    for col in df.columns:
        norm_col = col.lower().replace(" ", "")

        # Map based on substring patterns
        if "reportingweek" in norm_col:
            rename_map[col] = "Reporting Week"
        elif "vendorname" in norm_col:
            rename_map[col] = "Vendor Name"
        elif "division" in norm_col or "command" in norm_col:
            rename_map[col] = "Division/Command"
        elif "workproducttitle" in norm_col:
            rename_map[col] = "Work Product Title"
        elif "description" in norm_col and "contribution" in norm_col:
            rename_map[col] = "Brief description of individual's contribution"
        elif "workproductstatus" in norm_col or "status" in norm_col:
            rename_map[col] = "Work Product Status"
        elif "plannedorunplanned" in norm_col or "pmr" in norm_col:
            rename_map[col] = "Planned or Unplanned"
        elif "completeddate" in norm_col:
            rename_map[col] = "If Completed, Date Completed"
        elif "nfr" in norm_col:
            rename_map[col] = "Distinct NFR"
        elif "cap" in norm_col:
            rename_map[col] = "Distinct CAP"
        elif "levelofeffort" in norm_col or "percentage" in norm_col:
            rename_map[col] = "Level of Effort (%)"
        elif "contractor" in norm_col and "last" in norm_col:
            rename_map[col] = "Contractor (Last Name, First Name)"
        elif "govtta" in norm_col and "last" in norm_col:
            rename_map[col] = "Govt TA* (Last Name, First Name)"
        elif "laborcategory" in norm_col:
            rename_map[col] = "Labor Category*"

    df.rename(columns=rename_map, inplace=True)
    return df

def detect_header_row(excel_file, expected_keywords, max_scan_rows=10):
    preview = pd.read_excel(excel_file, header=None, nrows=max_scan_rows)
    best_row_index = -1
    max_matches = 0

    for i in range(len(preview)):
        row = preview.iloc[i].fillna("").astype(str)
        joined = " ".join(row.values).lower().replace(" ", "")
        matches = sum(1 for keyword in expected_keywords if keyword in joined)
        if matches > max_matches:
            max_matches = matches
            best_row_index = i

    return best_row_index if max_matches > 0 else None

# Storage
DATA_FILE = "data/submissions.csv"
os.makedirs("data", exist_ok=True)

st.subheader("📥 Upload Pre-filled Excel File (Optional)")
uploaded_file = st.file_uploader("Upload .xlsx file with WSR format", type=["xlsx"])

if uploaded_file:
    try:
        expected_keywords = [
            "reportingweek", "vendor", "division", "workproducttitle",
            "contractor", "govtta", "levelofeffort", "status", "planned"
        ]

        header_row = detect_header_row(uploaded_file, expected_keywords)

        if header_row is not None:
            uploaded_df = pd.read_excel(uploaded_file, header=header_row)
            uploaded_df = normalize_columns(uploaded_df)
        else:
            st.error("Could not detect a valid header row in the uploaded file.")
            st.stop()


        # Normalize column headers
        uploaded_df = normalize_columns(uploaded_df)

        if os.path.exists(DATA_FILE):
            existing_df = pd.read_csv(DATA_FILE)
            existing_df = normalize_columns(existing_df)
            combined_df = pd.concat([existing_df, uploaded_df], ignore_index=True)
        else:
            combined_df = uploaded_df

        combined_df.to_csv(DATA_FILE, index=False)
        st.success(f"Uploaded and saved {len(uploaded_df)} rows successfully.")
    except Exception as e:
        st.error(f"Upload failed: {e}")
       
# st.divider()
# st.subheader("📝 Manual Entry Form")



# Form
with st.form(key='report_form'):
    reporting_week = st.date_input("Reporting Week (MM/DD/YYYY)")
    vendor_name = st.text_input("Vendor Name*", max_chars=100)
    division_command = st.text_input("Division/Command", max_chars=100)
    work_product_title = st.text_input("Work Product Title", max_chars=100)
    contribution_desc = st.text_area("Brief description of individual's contribution")
    work_product_status = st.selectbox("Work Product Status*", ["In Progress", "Completed", "On Hold"])
    planned_unplanned = st.selectbox("Planned or Unplanned* (based on Monthly PMR)", ["Planned", "Unplanned"])
    date_completed = st.date_input("If Completed, Date Completed")
    distinct_nfr = st.text_input("Distinct NFR", max_chars=100)
    distinct_cap = st.text_input("Distinct CAP", max_chars=100)
    level_of_effort = st.slider("Level of Effort (%)", 0, 100, 50)
    contractor_name = st.text_input("Contractor (Last Name, First Name)", max_chars=100)
    govt_ta_name = st.text_input("Govt TA* (Last Name, First Name)", max_chars=100)
    lcat = st.text_input("Labor Category*", max_chars=100)

   
    submitted = st.form_submit_button("Submit")
   
    if submitted:
        new_data = {
            "Reporting Week": reporting_week,
            "Vendor Name": vendor_name,
            "Division/Command": division_command,
            "Work Product Title": work_product_title,
            "Brief description of individual's contribution": contribution_desc,
            "Work Product Status": work_product_status,
            "Planned or Unplanned": planned_unplanned,
            "If Completed, Date Completed": date_completed,
            "Distinct NFR": distinct_nfr,
            "Distinct CAP": distinct_cap,
            "Level of Effort (%)": level_of_effort,
            "Contractor (Last Name, First Name)": contractor_name,
            "Govt TA* (Last Name, First Name)": govt_ta_name,
            "Labor Category*": lcat,

        }
       
        if os.path.exists(DATA_FILE):
            df = pd.read_csv(DATA_FILE)
            df = normalize_columns(df)
            df = pd.concat([df, pd.DataFrame([new_data])], ignore_index=True)
        else:
            df = pd.DataFrame([new_data])
       
        df.to_csv(DATA_FILE, index=False)
        st.success("Report submitted successfully!")

def export_to_excel_microsoft_graph(data_dict):
    access_token = get_token()

    # Convert to Excel file
    temp_file = "data/temp_submission.xlsx"
    df = pd.DataFrame([data_dict])
    df.to_excel(temp_file, index=False)

    # Set OneDrive path (personal or org)
    filename = "WSR_Submissions.xlsx"
    upload_url = f"https://graph.microsoft.com/v1.0/me/drive/root:/WSR/{filename}:/content"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    }

    with open(temp_file, "rb") as f:
        res = requests.put(upload_url, headers=headers, data=f)

    if res.status_code in [200, 201]:
        st.success("Uploaded to OneDrive successfully!")
    else:
        st.error(f"Upload failed: {res.text}")
       
export_to_excel_microsoft_graph(new_data)
