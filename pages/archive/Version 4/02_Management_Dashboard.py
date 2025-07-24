# Import necessary libraries
import streamlit as st  # For creating the interactive web app
from sqlalchemy import create_engine, text  # For database connection and raw SQL execution
import pandas as pd  # For working with tabular data
import plotly.express as px  # For creating visualizations
import re  # For text cleaning using regular expressions

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

####################
# --- DB Setup ---
####################
# Connect to the PostgreSQL database using SQLAlchemy
DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/Iberia_BackOffice"
engine = create_engine(DATABASE_URL)

##############################################
# --- SQL Query to Pull Weekly Report Data ---
##############################################
# Query joins weekly reports with employee details
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

##################################
# --- Fetch Data from Database ---
##################################
# Execute SQL query and store the result in a DataFrame
with engine.connect() as conn:
    result = conn.execute(text(query))
    df = pd.DataFrame(result.fetchall(), columns=result.keys())

#####################################
# --- Cleanup and Standardization ---
#####################################
# Clean column names (remove extra spaces or special characters)
df.columns = [re.sub(r'\s+', ' ', col).replace("*", "").strip() for col in df.columns]

# Check if required columns are present
required_cols = [
    "Vendor Name", "Division/Command", "Work Product Title",
    "Level of Effort (%)", "Reporting Week",
    "Contractor (Last Name, First Name)", "Govt TA (Last Name, First Name)",
    "Work Product Status", "Planned or Unplanned"
]
missing_required = [col for col in required_cols if col not in df.columns]
if missing_required:
    st.error(f"Missing required columns: {missing_required}")
    st.stop()


############################
# --- Data Preprocessing ---
############################
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
week_strs = df["Reporting Week"].dropna().dt.strftime("%Y-%m-%d").unique()
selected_week_strs = st.sidebar.multiselect("Reporting Week", sorted(week_strs))
selected_vendor = st.sidebar.multiselect("Vendor", sorted(df["Vendor Name"].dropna().unique()))
selected_contractor = st.sidebar.multiselect("Contractor", sorted(df["Contractor (Last Name, First Name)"].dropna().unique()))

# Apply filters
if selected_week_strs:
    week_dates = pd.to_datetime(selected_week_strs)
    df = df[df["Reporting Week"].isin(week_dates)]
if selected_vendor:
    df = df[df["Vendor Name"].isin(selected_vendor)]
if selected_contractor:
    df = df[df["Contractor (Last Name, First Name)"].isin(selected_contractor)]

####################
# --- Export CSV ---
####################
# Allow user to download the filtered data
st.download_button(
    label="📁 Download Filtered Data as CSV",
    data=df.to_csv(index=False).encode("utf-8"),
    file_name="filtered_team_performance.csv",
    mime="text/csv"
)

# ==========================
# TABLE PREVIEW SECTION
# ==========================
# Filtered Data
st.subheader("Filtered Results")
st.dataframe(df, use_container_width=True)

if df.empty:
    st.warning("No records match your filter criteria.")
    st.stop()

########################
# --- Visualizations ---
########################
# Treemap
st.subheader("Effort Breakdown: Vendor → Division → Contractor → Work Product")
try:
    fig = px.treemap(
        df,
        path=["Vendor Name", "Division/Command", "Contractor (Last Name, First Name)", "Work Product Title"],
        values="Level of Effort (%)",
        hover_data=["Work Product Status", "Planned or Unplanned", "Govt TA (Last Name, First Name)"],
    )
    st.plotly_chart(fig, use_container_width=True)
except ValueError as ve:
    st.error(f"Treemap failed: {ve}")


# st.markdown("---")

# col1, col2 = st.columns(2)

# # --- Bar Chart: Effort by Division ---
# with col1:
#     st.subheader("Effort by Division")
#     div_effort = df.groupby("Division/Command")["Level of Effort (%)"].sum().sort_values(ascending=False)
#     st.bar_chart(div_effort)

#     # --- Pie Chart: Work Product Status ---
# with col2:
#     st.subheader("Work Product Status Distribution")
#     status_counts = df["Work Product Status"].value_counts()
#     st.plotly_chart(
#         px.pie(names=status_counts.index, values=status_counts.values, title="Status Breakdown"),
#         use_container_width=True
#     )

# # --- Weekly Completion Trend ---
# st.subheader("Weekly Completion Trend")
# completed = df[df["Work Product Status"].str.lower() == "completed"]
# trend = completed.groupby(df["Reporting Week"].dt.to_period("W").dt.start_time).size()
# st.line_chart(trend)


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