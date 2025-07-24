import streamlit as st
from sqlalchemy import create_engine, text
import pandas as pd
import plotly.express as px
import re

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
    wr.govttaname AS "Govt TA (Last Name, First Name)",
    e.laborcategory AS "Labor Category"
FROM weeklyreports wr
JOIN employees e ON wr.employeeid = e.employeeid
"""

with engine.connect() as conn:
    result = conn.execute(text(query))
    df = pd.DataFrame(result.fetchall(), columns=result.keys())


# Normalize columns: remove extra spaces and stars
df.columns = [re.sub(r'\s+', ' ', str(col)).replace("*", "").strip() for col in df.columns]

required_cols = [
    "Vendor Name",
    "Division/Command",
    "Work Product Title",
    "Level of Effort (%)",
    "Reporting Week",
    "Contractor (Last Name, First Name)",
    "Govt TA (Last Name, First Name)",
    "Work Product Status",
    "Planned or Unplanned",
]

missing_required = [col for col in required_cols if col not in df.columns]

if missing_required:
    st.error(f"❌ Missing required columns: {missing_required}")
    st.stop()

# Convert Reporting Week to datetime
df["Reporting Week"] = pd.to_datetime(df["Reporting Week"], errors='coerce')

# Sidebar filters
st.sidebar.header("🔍 Filters")

unique_weeks = df["Reporting Week"].dropna().dt.strftime("%Y-%m-%d").unique()
selected_week_strs = st.sidebar.multiselect("Reporting Week", sorted(unique_weeks))

selected_vendor = []
if "Vendor Name" in df.columns:
    selected_vendor = st.sidebar.multiselect("Vendor Name", sorted(df["Vendor Name"].dropna().unique()))
else:
    st.sidebar.warning("Missing column: Vendor Name")

contractor_col = "Contractor (Last Name, First Name)"
selected_contractor = []
if contractor_col in df.columns:
    selected_contractor = st.sidebar.multiselect("Contractor", sorted(df[contractor_col].dropna().unique()))
else:
    st.sidebar.warning(f"Missing column: {contractor_col}")

# Apply filters
if selected_week_strs:
    selected_week = pd.to_datetime(selected_week_strs)
    df = df[df["Reporting Week"].isin(selected_week)]
if selected_vendor:
    df = df[df["Vendor Name"].isin(selected_vendor)]
if selected_contractor:
    df = df[df[contractor_col].isin(selected_contractor)]

# Show filtered data
st.subheader("📋 Filtered Data View")
st.dataframe(df, use_container_width=True)

if df.empty:
    st.warning("No records match your filter criteria.")
    st.stop()

# Clean Level of Effort column
if df["Level of Effort (%)"].dtype == object:
    # Convert everything to string first (safely), replace %, then convert to float
    df["Level of Effort (%)"] = (
        df["Level of Effort (%)"]
        .astype(str)
        .str.replace('%', '', regex=False)
    )

    # Convert to float, coercing errors to NaN
    df["Level of Effort (%)"] = pd.to_numeric(df["Level of Effort (%)"], errors='coerce')


# Treemap
st.subheader("📌 Hierarchical Drilldown: Vendor → Division → Contractor → Work Product Title")

path_columns = ["Vendor Name", "Division/Command"]
if "Contractor (Last Name, First Name)" in df.columns:
    path_columns.append("Contractor (Last Name, First Name)")
path_columns.append("Work Product Title")

try:
    fig = px.treemap(
        df,
        path=path_columns,
        values="Level of Effort (%)",
        hover_data=["Work Product Status", "Planned or Unplanned", "Govt TA (Last Name, First Name)"],
    )
    st.plotly_chart(fig, use_container_width=True)
except ValueError as ve:
    st.error(f"Treemap failed: {ve}")
