# Import necessary libraries
import streamlit as st  # For creating the interactive web app
from sqlalchemy import text  # For database connection and raw SQL execution
import pandas as pd  # For working with tabular data
import plotly.express as px  # For creating visualizations
import re  # For text cleaning using regular expressions

# Import shared modules
from utils.db import get_engine
from utils.queries import weekly_reports_with_employees


############################
# --- Page Configuration ---
############################
st.set_page_config(
    # browser tab title
    page_title="Management Dashboard", 
    # wide layout for more screen space
    layout="wide")

#######################
# --- Logo Display ---
#######################
# Display logo at top of app (ensure image path points to valid directory)
st.image("images/Iberia-Advisory.png", width=250)

####################################
# --- Page Title and Description ---
####################################
# Display the main title and a short description below it
st.title("Management Dashboard") 
st.caption("Visualize and filter team effort across vendors, divisions, and contractors.")

############################
# --- Load Weekly Report Data ---
############################
@st.cache_data(ttl=600)
def load_weekly_data():
    with get_engine().connect() as conn:
        result = conn.execute(text(weekly_reports_with_employees))
        df = pd.DataFrame(result.fetchall(), columns=result.keys())

    df.columns = [re.sub(r"\s+", " ", col).strip() for col in df.columns]
    return df

df = load_weekly_data()

#########################
# --- Data Preparation ---
#########################

# Check if required columns are present
required_cols = [
    "Vendor Name", "Division/Command", "Work Product Title",
    "Level of Effort (%)", "Reporting Week",
    "Contractor (Last Name, First Name)", "Govt TA (Last Name, First Name)",
    "Work Product Status", "Planned or Unplanned"
]

missing_cols = [col for col in required_cols if col not in df.columns]
if missing_cols:
    st.error(f"Missing required columns: {missing_cols}")
    st.stop()

# Convert reporting week to datetime
df["Reporting Week"] = pd.to_datetime(df["Reporting Week"], errors='coerce')

# Convert level of effort to numeric (strip % if present)
df["Level of Effort (%)"] = pd.to_numeric(
    df["Level of Effort (%)"].astype(str).str.replace('%', '', regex=False),
    errors='coerce'
).fillna(0)

# Calculate hours worked assuming 40 hours is 100% effort
df["Hours"] = (df["Level of Effort (%)"] / 100 * 40).round(2)

#########################
# --- Sidebar Filters ---
#########################
st.sidebar.header("Filter Data")

# Create dropdowns/multiselects based on available data
week_options = df["Reporting Week"].dropna().dt.strftime("%Y-%m-%d").sort_values().unique()
selected_weeks = st.sidebar.multiselect("Reporting Week", week_options)

vendors = df["Vendor Name"].dropna().sort_values().unique()
selected_vendors = st.sidebar.multiselect("Vendor", vendors)

contractors = df["Contractor (Last Name, First Name)"].dropna().sort_values().unique()
selected_contractors = st.sidebar.multiselect("Contractor", contractors)

# Apply filters
if selected_weeks:
    df = df[df["Reporting Week"].dt.strftime("%Y-%m-%d").isin(selected_weeks)]
if selected_vendors:
    df = df[df["Vendor Name"].isin(selected_vendors)]
if selected_contractors:
    df = df[df["Contractor (Last Name, First Name)"].isin(selected_contractors)]

####################
# --- Export CSV ---
####################
st.download_button(
    label="📁 Download Filtered Data as CSV",
    data=df.to_csv(index=False).encode("utf-8"),
    file_name="filtered_team_performance.csv",
    mime="text/csv"
)

########################
# --- Filtered Table ---
########################
# Filtered Data
st.subheader("Filtered Results")
st.dataframe(df, use_container_width=True)

if df.empty:
    st.warning("No records match your filter criteria.")
    st.stop()

########################
# --- Treemap Chart ---
########################
# Treemap
st.subheader("Effort Breakdown: Vendor → Division → Contractor → Work Product")
try:
    fig = px.treemap(
        df,
        path=[
            "Vendor Name",
            "Division/Command",
            "Contractor (Last Name, First Name)",
            "Work Product Title"
        ],
        values="Level of Effort (%)",
        hover_data=[
            "Work Product Status",
            "Planned or Unplanned",
            "Govt TA (Last Name, First Name)"
        ]
    )
    st.plotly_chart(fig, use_container_width=True)
except ValueError as ve:
    st.error(f"Treemap failed to render: {ve}")

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