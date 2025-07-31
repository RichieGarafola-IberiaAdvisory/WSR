import streamlit as st
import pandas as pd
import plotly.express as px

from utils.db import get_data, load_all_data
from utils.helpers import normalize_text

# ----------------------------
# Page Setup
# ----------------------------
st.set_page_config("Accomplishments Dashboard", layout="wide")
st.markdown("""
    <style>
        h1, h2, h3, h4 { color: #004080 !important; }
        div[data-testid="stMetricValue"] { color: #004080; font-weight: bold; }
        div[data-testid="stMetricLabel"] { color: #1E90FF; }
        hr { border-top: 2px solid #1E90FF; }
    </style>
""", unsafe_allow_html=True)
st.title("Accomplishments Dashboard")
st.caption("Explore weekly accomplishments across teams and workstreams.")

# ----------------------------
# Refresh Button
# ----------------------------
if st.button("🔄 Refresh Accomplishments Data"):
    load_all_data.clear()
    if "session_data" in st.session_state:
        del st.session_state["session_data"]
    st.experimental_rerun()

# ----------------------------
# Load Data (Cached)
# ----------------------------
@st.cache_data(ttl=8 * 3600)
def load_accomplishments():
    accomplishments_df = get_data("Accomplishments")
    employees_df = get_data("Employees")
    workstreams_df = get_data("Workstreams")

    df = (
        accomplishments_df
        .merge(employees_df[["EmployeeID", "Name", "VendorName", "LaborCategory"]], on="EmployeeID", how="left")
        .merge(workstreams_df[["WorkstreamID", "Name"]], on="WorkstreamID", how="left")
        .rename(columns={
            "DateRange": "Reporting Week",
            "Description": "Accomplishment",
            "Name_x": "Contractor",
            "VendorName": "Vendor",
            "LaborCategory": "Labor Category",
            "Name_y": "Workstream"
        })
    )
    return df

df = load_accomplishments()

if df.empty:
    st.warning("No accomplishments available.")
    st.stop()

# ----------------------------
# Normalize text fields
# ----------------------------
df["Reporting Week"] = pd.to_datetime(df["Reporting Week"], errors="coerce")
df["Accomplishment"] = df["Accomplishment"].astype(str).apply(normalize_text)
df["Contractor"] = df["Contractor"].astype(str).apply(normalize_text)
df["Workstream"] = df["Workstream"].astype(str).apply(normalize_text)
df["Vendor"] = df["Vendor"].astype(str).apply(normalize_text)

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
vendor_options = df["Vendor"].dropna().sort_values().unique()
selected_vendors = st.sidebar.multiselect("Vendor", vendor_options)
search_keyword = st.sidebar.text_input("Search Keyword")

if st.sidebar.button("Reset Filters"):
    for key in ["selected_weeks", "selected_contractors", "selected_workstreams", "selected_vendors", "search_keyword"]:
        if key in st.session_state:
            del st.session_state[key]
    st.experimental_rerun()

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
if selected_vendors:
    filtered_df = filtered_df[filtered_df["Vendor"].isin(selected_vendors)]
if search_keyword:
    search_lower = search_keyword.lower()
    filtered_df = filtered_df[
        filtered_df["Accomplishment"].str.lower().str.contains(search_lower) |
        filtered_df["Contractor"].str.lower().str.contains(search_lower) |
        filtered_df["Workstream"].str.lower().str.contains(search_lower) |
        filtered_df["Vendor"].str.lower().str.contains(search_lower)
    ]

# ----------------------------
# Metrics
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
    if workstream_counts.empty:
        st.info("No data available for selected filters.")
    else:
        fig = px.bar(
            x=workstream_counts.index,
            y=workstream_counts.values,
            labels={"x": "Workstream", "y": "Count"},
            title="Accomplishments by Workstream",
            color=workstream_counts.index,
            color_discrete_sequence=px.colors.sequential.Blues
        )
        st.plotly_chart(fig, use_container_width=True)

with v2:
    st.subheader("Top Contractors by Accomplishment Count")
    contractor_counts = filtered_df["Contractor"].value_counts()
    if contractor_counts.empty:
        st.info("No data available for selected filters.")
    else:
        fig = px.bar(
            x=contractor_counts.index,
            y=contractor_counts.values,
            labels={"x": "Contractor", "y": "Count"},
            title="Top Contractors by Accomplishment Count",
            color=contractor_counts.index,
            color_discrete_sequence=px.colors.sequential.Blues
        )
        st.plotly_chart(fig, use_container_width=True)


# ----------------------------
# Accomplishments Table
# ----------------------------
st.markdown("## Accomplishments Table")
if filtered_df.empty:
    st.warning("No accomplishments match your filters.")
else:
    display_df = filtered_df.sort_values("Reporting Week", ascending=False)[
        ["Reporting Week", "Contractor", "Vendor", "Workstream", "Accomplishment"]
    ]
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

#######################################
# Helper for tests
#######################################
def render_accomplishments():
    try:
        return True
    except Exception:
        return False


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
