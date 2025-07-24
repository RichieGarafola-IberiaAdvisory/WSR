import streamlit as st
from sqlalchemy import create_engine
import pandas as pd
import plotly.express as px
import os
import re

# DB connection
DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/Iberia_BackOffice"
engine = create_engine(DATABASE_URL)

st.title("📊 Management Dashboard")



query = """
SELECT 
    wr.weekstartdate AS "Reporting Week",
    e.vendorname AS "Vendor Name",
    wr.divisioncommand AS "Division/Command",
    wr.workproducttitle AS "Work Product Title",
    wr.contributiondescription AS "Brief description of individual's contribution",
    wr.status AS "Work Product Status",
    wr.plannedorunplanned AS "Planned or Unplanned",
    wr.datecompleted AS "If Completed, Date Completed",
    wr.distinctnfr AS "Distinct NFR",
    wr.distinctcap AS "Distinct CAP",
    wr.effortpercentage AS "Level of Effort (%)",
    e.name AS "Contractor (Last Name, First Name)",
    wr.govttaname AS "Govt TA* (Last Name, First Name)",
    e.laborcategory AS "Labor Category"
FROM weeklyreports wr
JOIN employees e ON wr.employeeid = e.employeeid
"""

# Load data
raw_conn = engine.raw_connection()
try:
    df = pd.read_sql_query(query, con=raw_conn)
finally:
    raw_conn.close()


# Normalize columns if needed
def normalize_columns(df):
    import re
    df.columns = [re.sub(r'\s+', ' ', str(col)).replace("*", "").strip() for col in df.columns]
    # Your rename_map logic here if needed...
    return df

df = normalize_columns(df)

# 🔍 Required and optional columns
required_cols = [
    "Vendor Name",
    "Division/Command",
    "Work Product Title",
    "Level of Effort (%)",
    "Reporting Week",
    "Contractor (Last Name, First Name)",
    "Govt TA (Last Name, First Name)",  # NO star here
    "Work Product Status",
    "Planned or Unplanned",
]

# 🚨 Check for missing required columns
missing_required = [col for col in required_cols if col not in df.columns]


if missing_required:
    st.error(f"❌ Missing required columns: {missing_required}")
    st.stop()




# Ensure Reporting Week is datetime
df["Reporting Week"] = pd.to_datetime(df["Reporting Week"], errors='coerce')

# Sidebar filters
st.sidebar.header("🔍 Filters")

unique_weeks = df["Reporting Week"].dropna().dt.strftime("%Y-%m-%d").unique()
selected_week_strs = st.sidebar.multiselect("Reporting Week", sorted(unique_weeks))

# Vendor filter
if "Vendor Name" in df.columns:
    selected_vendor = st.sidebar.multiselect("Vendor Name", sorted(df["Vendor Name"].dropna().unique()))
else:
    selected_vendor = []
    st.sidebar.warning("Missing column: Vendor Name")

# Contractor filter
contractor_col = "Contractor (Last Name, First Name)"
if contractor_col in df.columns:
    selected_contractor = st.sidebar.multiselect("Contractor", sorted(df[contractor_col].dropna().unique()))
else:
    selected_contractor = []
    st.sidebar.warning(f"Missing column: {contractor_col}")

# Apply filters
if selected_week_strs:
    selected_week = pd.to_datetime(selected_week_strs)
    df = df[df["Reporting Week"].isin(selected_week)]
if selected_vendor:
    df = df[df["Vendor Name"].isin(selected_vendor)]
if selected_contractor:
    df = df[df[contractor_col].isin(selected_contractor)]

# Display filtered data
st.subheader("📋 Filtered Data View")
st.dataframe(df, use_container_width=True)

if df.empty:
    st.warning("No records match your filter criteria.")
    st.stop()

# Clean Level of Effort column if needed
if df["Level of Effort (%)"].dtype == object:
    df["Level of Effort (%)"] = df["Level of Effort (%)"].str.replace('%', '', regex=False).astype(float)

# Prepare hover fields safely
hover_fields = ["Work Product Status", "Planned or Unplanned"]
govt_ta_col = "Govt TA (Last Name, First Name)"
if govt_ta_col in df.columns:
    hover_fields.append(govt_ta_col)

# Treemap visualization
st.subheader("📌 Hierarchical Drilldown: Vendor → Division → Contractor → Work Product Title")

# Build treemap path dynamically based on available columns
path_columns = ["Vendor Name", "Division/Command"]
if "Contractor (Last Name, First Name)" in df.columns:
    path_columns.append("Contractor (Last Name, First Name)")
path_columns.append("Work Product Title")

# Build the treemap
try:
    fig = px.treemap(
        df,
        path=path_columns,
        values="Level of Effort (%)",
        hover_data=hover_fields,
    )
    st.plotly_chart(fig, use_container_width=True)
except ValueError as ve:
    st.error(f"Treemap failed: {ve}")


