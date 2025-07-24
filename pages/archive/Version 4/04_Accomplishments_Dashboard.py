import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, MetaData, select, join
import plotly.express as px

# ----------------------------
# Page Setup
# ----------------------------
st.set_page_config("🏆 Accomplishments Dashboard", layout="wide")
st.title("🏆 Accomplishments Dashboard")
st.caption("Explore weekly accomplishments across teams and workstreams.")

# ----------------------------
# DB Setup
# ----------------------------
DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/Iberia_BackOffice"
engine = create_engine(DATABASE_URL)
metadata = MetaData()
metadata.reflect(bind=engine)

# Reference tables
employees = metadata.tables["employees"]
workstreams = metadata.tables["workstreams"]
weekly_reports = metadata.tables["weeklyreports"]
accomplishments = metadata.tables["accomplishments"]
hourstracking = metadata.tables["hourstracking"]

# ----------------------------
# Load and Join Data
# ----------------------------
@st.cache_data(ttl=600)
def load_accomplishments():
    j = join(accomplishments, employees, accomplishments.c.employeeid == employees.c.employeeid).join(
        workstreams, accomplishments.c.workstreamid == workstreams.c.workstreamid
    )
    stmt = select(
        accomplishments.c.daterange,
        accomplishments.c.description,
        employees.c.name.label("Employee"),
        employees.c.vendorname.label("Vendor"),
        employees.c.laborcategory.label("Labor Category"),
        workstreams.c.name.label("Workstream"),
    ).select_from(j)

    with engine.connect() as conn:
        df = pd.DataFrame(conn.execute(stmt).fetchall(), columns=stmt.columns.keys())

    return df


df = load_accomplishments()

# ----------------------------
# Sidebar Filters
# ----------------------------
st.sidebar.header("🔍 Filter Accomplishments")
unique_weeks = df["daterange"].dropna().unique()
selected_weeks = st.sidebar.multiselect("📅 Reporting Week", sorted(unique_weeks))
selected_contractors = st.sidebar.multiselect("👷 Contractor", sorted(df["Employee"].dropna().unique()))
selected_workstreams = st.sidebar.multiselect("🧩 Workstream", sorted(df["Workstream"].dropna().unique()))
search_keyword = st.sidebar.text_input("🔎 Search Keyword")

# ----------------------------
# Apply Filters
# ----------------------------
filtered_df = df.copy()
if selected_weeks:
    week_dates = pd.to_datetime(selected_weeks)
    filtered_df = filtered_df[filtered_df["reportingweek"].isin(week_dates)]

if selected_contractors:
    filtered_df = filtered_df[filtered_df["Employee"].isin(selected_contractors)]

if selected_workstreams:
    filtered_df = filtered_df[filtered_df["Workstream"].isin(selected_workstreams)]

if search_keyword:
    filtered_df = filtered_df[
        filtered_df["accomplishmenttext"]
        .str.lower()
        .str.contains(search_keyword.lower())
    ]

# ----------------------------
# Top-Level Metrics
# ----------------------------
k1, k2 = st.columns(2)
k1.metric("Total Accomplishments", len(filtered_df))
k2.metric("Unique Contractors", filtered_df["Employee"].nunique())

# ----------------------------
# Visualizations
# ----------------------------
v1, v2 = st.columns(2)

with v1:
    st.subheader("📊 Accomplishments by Workstream")
    workstream_counts = filtered_df["Workstream"].value_counts()
    st.bar_chart(workstream_counts)

with v2:
    st.subheader("👷 Top Contractors by Accomplishment Count")
    contractor_counts = filtered_df["Employee"].value_counts()
    st.bar_chart(contractor_counts)

# ----------------------------
# Accomplishments Table
# ----------------------------
st.markdown("## 📋 Accomplishments Table")
if filtered_df.empty:
    st.warning("⚠️ No accomplishments match your filters.")
else:
    styled_df = filtered_df.sort_values("daterange", ascending=False).rename(columns={
        "daterange": "Reporting Week",
        "description": "Accomplishment"
    })

    st.dataframe(styled_df, use_container_width=True)

# ----------------------------
# Export Option
# ----------------------------
st.download_button(
    label="📁 Download Filtered Accomplishments",
    data=styled_df.to_csv(index=False).encode("utf-8"),
    file_name="filtered_accomplishments.csv",
    mime="text/csv"
)
