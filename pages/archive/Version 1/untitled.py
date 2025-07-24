import streamlit as st
from sqlalchemy import create_engine, MetaData, Table, select, join
import pandas as pd
import plotly.express as px
import os

st.set_page_config(page_title="HR Dashboard", layout="wide")
st.title("📊 HR Management Dashboard")

DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/Iberia_BackOffice"
engine = create_engine(DATABASE_URL)

# Reflect metadata and get the WeeklyReports table (adjust table name if different)
metadata = MetaData()
metadata.reflect(bind=engine)
weekly_reports = metadata.tables['weeklyreports']
employees = metadata.tables['employees']

@st.cache_data(ttl=600)
def load_weekly_reports_with_labors():
    j = join(weekly_reports, employees, weekly_reports.c.employeeid == employees.c.employeeid)
    stmt = select(
        weekly_reports,
        employees.c.laborcategory
    ).select_from(j)
    
    with engine.connect() as conn:
        result = conn.execute(stmt)
        df = pd.DataFrame(result.fetchall(), columns=result.keys())

    # Rename columns to match your existing code expectations:
    df.rename(columns={
        'weekstartdate': 'Reporting Week',
        'datecompleted': 'If Completed, Date Completed',
        'status': 'Work Product Status',
        'plannedorunplanned': 'Planned or Unplanned',
        'effortpercentage': 'Level of Effort (%)',
        'contractorname': 'Contractor (Last Name, First Name)',
        'workproducttitle': 'Work Product Title',
        'divisioncommand': 'Division/Command',
        'govttaname': 'GovtTAName',
        'distinctnfr': 'DistinctNFR',
        'distinctcap': 'DistinctCAP',
        'laborcategory': 'Labor Category*',
    }, inplace=True)

    return df

df = load_weekly_reports_with_labors()


# Data normalization
df["Reporting Week"] = pd.to_datetime(df["Reporting Week"], errors='coerce')
df["If Completed, Date Completed"] = pd.to_datetime(df["If Completed, Date Completed"], errors='coerce')
df["Work Product Status"] = df["Work Product Status"].astype(str).str.strip().str.title()
df["Planned or Unplanned"] = df["Planned or Unplanned"].astype(str).str.strip().str.lower()

df["Level of Effort (%)"] = pd.to_numeric(df["Level of Effort (%)"], errors='coerce').fillna(0)
df["Hours"] = (df["Level of Effort (%)"] / 100 * 40).round(2)

# KPIs
total_hours = df["Hours"].sum()
avg_hours_per_contractor = df.groupby("Contractor (Last Name, First Name)")["Hours"].sum().mean()

unplanned_hours = df[df["Planned or Unplanned"] == "unplanned"]["Hours"].sum()
unplanned_pct = (unplanned_hours / total_hours * 100) if total_hours > 0 else 0

reported_contractors = df["Contractor (Last Name, First Name)"].nunique()
all_possible_contractors = {
    "Smith, John", "Doe, Jane", "Lee, Kevin", "Patel, Anjali", "Taylor, Morgan",
    "Nguyen, Linh", "Reed, Marcus", "Foster, Ava", "Rodriguez, Miguel", "Wright, Emily",
    "Clark, Sam", "Perry, Nina", "White, Jonah", "Kumar, Priya", "Brooks, Zoe",
    "Turner, Eli", "Price, Mia", "Hall, Owen", "Bell, Ruby", "Adams, Jack"
}
missing_contractors = sorted(all_possible_contractors - set(df["Contractor (Last Name, First Name)"].dropna().unique()))

# KPI Section
st.subheader("📌 Key Performance Indicators")
k1, k2, k3, k4 = st.columns(4)
k1.metric("Total Hours Worked", f"{total_hours:.1f}")
k2.metric("Avg Hours / Contractor", f"{avg_hours_per_contractor:.1f}")
k3.metric("Unplanned Hours %", f"{unplanned_pct:.1f}%")
k4.metric("Non-reporting Contractors", len(missing_contractors))

# Status Breakdown
st.subheader("📊 Work Product Status")
status_counts = df["Work Product Status"].value_counts()
st.bar_chart(status_counts)

# Weekly Completions
st.subheader("📅 Weekly Completion Trend")
weekly_completions = (
    df[df["Work Product Status"] == "Completed"]
    .groupby(df["Reporting Week"].dt.to_period("W").dt.start_time)
    .size()
)
st.line_chart(weekly_completions)

# Top Work Products
st.subheader("🏆 Top 5 Work Product Titles")
top_titles = df["Work Product Title"].value_counts().head(5)
st.table(top_titles)

# Division Breakdown
st.subheader("🏢 Effort by Division")
division_effort = df.groupby("Division/Command")["Level of Effort (%)"].sum().sort_values(ascending=False)
st.bar_chart(division_effort)

# Unplanned Hours by Division
st.subheader("⚠️ Unplanned Hours by Division")
unplanned_by_div = (
    df[df["Planned or Unplanned"] == "unplanned"]
    .groupby("Division/Command")["Hours"]
    .sum()
    .sort_values(ascending=False)
)
st.bar_chart(unplanned_by_div)

# Labor Category
st.subheader("👷 Labor Category Distribution")
labor_dist = df["Labor Category*"].value_counts()
st.plotly_chart(
    px.pie(
        names=labor_dist.index,
        values=labor_dist.values,
        title="Labor Categories"
    ),
    use_container_width=True
)

# Monthly Heatmap
st.subheader("📆 Monthly Hours Heatmap by Contractor")
heatmap_df = (
    df.dropna(subset=["Reporting Week"])
    .assign(Month=df["Reporting Week"].dt.to_period("M").astype(str))
    .groupby(["Contractor (Last Name, First Name)", "Month"])["Hours"]
    .sum()
    .reset_index()
    .pivot(index="Contractor (Last Name, First Name)", columns="Month", values="Hours")
    .fillna(0)
)

st.dataframe(
    heatmap_df.style.background_gradient(axis=1, cmap="Blues"),
    use_container_width=True
)

# Missing Contractor Alerts
st.subheader("🚩 Contractors with Zero Submissions")
if missing_contractors:
    st.warning(f"{len(missing_contractors)} contractors have no submissions.")
    st.write(missing_contractors)
else:
    st.success("✅ All expected contractors have submitted.")
