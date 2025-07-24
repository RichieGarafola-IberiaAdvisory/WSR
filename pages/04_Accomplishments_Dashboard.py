import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import select, join

from utils.db import engine, employees, accomplishments, workstreams
from utils.helpers import normalize_text

# ----------------------------
# Page Setup
# ----------------------------
st.set_page_config("Accomplishments Dashboard", layout="wide")
st.title("Accomplishments Dashboard")
st.caption("Explore weekly accomplishments across teams and workstreams.")

# ----------------------------
# Load Data (w/ Join)
# ----------------------------
@st.cache_data(ttl=600)
def load_accomplishments():
    j = join(
        accomplishments,
        employees, accomplishments.c.employeeid == employees.c.employeeid
    ).join(
        workstreams, accomplishments.c.workstreamid == workstreams.c.workstreamid
    )

    stmt = select(
        accomplishments.c.daterange,
        accomplishments.c.description,
        employees.c.name.label("Contractor"),
        employees.c.vendorname.label("Vendor"),
        employees.c.laborcategory.label("Labor Category"),
        workstreams.c.name.label("Workstream")
    ).select_from(j)

    with engine.connect() as conn:
        df = pd.DataFrame(conn.execute(stmt).fetchall(), columns=stmt.columns.keys())
    return df

df = load_accomplishments()

# ----------------------------
# Input Normalization
# ----------------------------
df["Reporting Week"] = pd.to_datetime(df["daterange"], errors="coerce")
df["Accomplishment"] = df["description"].astype(str).apply(normalize_text)
df["Contractor"] = df["Contractor"].astype(str).apply(normalize_text)
df["Workstream"] = df["Workstream"].astype(str).apply(normalize_text)

# ----------------------------
# Sidebar Filters
# ----------------------------
st.sidebar.header("Filter Accomplishments")

week_options = df["Reporting Week"].dropna().dt.strftime("%Y-%m-%d").sort_values().unique()
selected_weeks = st.sidebar.multiselect("Reporting Week", week_options)

contractor_options = df["Contractor"].dropna().sort_values().unique()
selected_contractors = st.sidebar.multiselect("Contractor", contractor_options)

workstream_options = df["Workstream"].dropna().sort_values().unique()
selected_workstreams = st.sidebar.multiselect("Workstream", workstream_options)

search_keyword = st.sidebar.text_input("Search Keyword (in accomplishments)")

# ----------------------------
# Apply Filters
# ----------------------------
filtered_df = df.copy()

if selected_weeks:
    selected_dates = pd.to_datetime(selected_weeks)
    filtered_df = filtered_df[filtered_df["Reporting Week"].isin(selected_dates)]

if selected_contractors:
    filtered_df = filtered_df[filtered_df["Contractor"].isin(selected_contractors)]

if selected_workstreams:
    filtered_df = filtered_df[filtered_df["Workstream"].isin(selected_workstreams)]

if search_keyword:
    filtered_df = filtered_df[filtered_df["Accomplishment"].str.lower().str.contains(search_keyword.lower())]

# ----------------------------
# Top-Level Metrics
# ----------------------------
k1, k2 = st.columns(2)
k1.metric("Total Accomplishments", len(filtered_df))
k2.metric("Unique Contractors", filtered_df["Contractor"].nunique())

# ----------------------------
# Visualizations
# ----------------------------
v1, v2 = st.columns(2)

with v1:
    st.subheader("Accomplishments by Workstream")
    workstream_counts = filtered_df["Workstream"].value_counts()
    st.bar_chart(workstream_counts)

with v2:
    st.subheader("Top Contractors by Accomplishment Count")
    contractor_counts = filtered_df["Contractor"].value_counts()
    st.bar_chart(contractor_counts)

# ----------------------------
# Accomplishments Table
# ----------------------------
st.markdown("## Accomplishments Table")
if filtered_df.empty:
    st.warning("No accomplishments match your filters.")
else:
    display_df = filtered_df.sort_values("Reporting Week", ascending=False)[[
        "Reporting Week", "Contractor", "Workstream", "Accomplishment"
    ]]
    st.dataframe(display_df, use_container_width=True)

# ----------------------------
# Export Option
# ----------------------------
st.download_button(
    label="📁 Download Filtered Accomplishments",
    data=display_df.to_csv(index=False).encode("utf-8") if not filtered_df.empty else "".encode("utf-8"),
    file_name="filtered_accomplishments.csv",
    mime="text/csv"
)


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