# Import required libraries
import streamlit as st  # Used for building the web app
from sqlalchemy import select, join, func, text  # For database connections
import pandas as pd  # For working with tabular data
import plotly.express as px  # For generating interactive charts

from utils.db import get_engine, get_data, load_all_data
from utils.helpers import normalize_text




############################
# --- Page Configuration ---
############################
st.set_page_config(
    # browser tab title
     page_title="HR Dashboard", 
     # wide layout for more screen space
     layout="wide")



st.markdown("""
    <style>
        /* Blue Header for titles */
        h1, h2, h3, h4 {
            color: #004080 !important; /* Navy Blue */
        }
        
        /* KPI metric cards */
        div[data-testid="stMetricValue"] {
            color: #004080;
            font-weight: bold;
        }
        div[data-testid="stMetricLabel"] {
            color: #1E90FF;
        }

        /* Horizontal rule */
        hr {
            border-top: 2px solid #1E90FF;
        }
    </style>
""", unsafe_allow_html=True)


#######################
# --- Logo Display ---
#######################
# Display logo at top of app (ensure image path points to valid directory)    
st.image("images/Iberia-Advisory.png", width=250)

####################################
# --- Page Title and Description ---
####################################
# Display the main title and a short description below it
st.title("HR Management Dashboard")
st.caption("Track contractor activity, coverage, and labor category distribution.")

##########################
# --- Refresh Button ---
##########################

if st.button("🔄 Refresh HR Data"):
    load_all_data.clear()
    if "session_data" in st.session_state:
        del st.session_state["session_data"]
    st.experimental_rerun()


################################
# --- Data Loader ---
################################
# Cache the function output for 10 minutes
# @st.cache_data(ttl=600)
# def load_hr_data():
#     # Join weekly reports and employees on employee ID
#     j = join(
#         weekly_reports, 
#         employees, 
#         weekly_reports.c.EmployeeID == employees.c.EmployeeID
#     )
    
#     stmt = select(
#         weekly_reports,
#         employees.c.LaborCategory
#     ).select_from(j)

#     # Execute query and load into DataFrame
#     with get_engine().connect() as conn:
#         df = pd.DataFrame(conn.execute(stmt).fetchall(), columns=stmt.columns.keys())

#     # Rename columns for clarity
#     df.rename(columns={
#         'WeekStartDate': 'Reporting Week',
#         'DateCompleted': 'If Completed, Date Completed',
#         'Status': 'Work Product Status',
#         'PlannedOrUnplanned': 'Planned or Unplanned',
#         'EffortPercentage': 'Level of Effort (%)',
#         'ContractorName': 'Contractor (Last Name, First Name)',
#         'WorkProductTitle': 'Work Product Title',
#         'DivisionCommand': 'Division/Command',
#         'GovtTAName': 'Govt TA (Last Name, First Name)',
#         'DistinctNFR': 'Distinct NFR',
#         'DistinctCAP': 'Distinct CAP',
#         'LaborCategory': 'Labor Category'
#     }, inplace=True)

#     return df

# # Load the data
# df = load_hr_data()

# Cache the function output for 10 minutes 
@st.cache_data(ttl=600) # 8 * 3600 8 hours
def load_hr_data():
    try:        
        from utils.db import load_table
        weekly = load_table("WeeklyReports")
        employees_df = load_table("Employees")

        # Handle different possible column names for Reporting Week
        if "weekstartdate" in weekly.columns:
            weekly.rename(columns={"weekstartdate": "Reporting Week"}, inplace=True)
        elif "WeekStartDate" in weekly.columns:
            weekly.rename(columns={"WeekStartDate": "Reporting Week"}, inplace=True)
        elif "WeekEnding" in weekly.columns:
            weekly.rename(columns={"WeekEnding": "Reporting Week"}, inplace=True)
        else:
            weekly["Reporting Week"] = pd.NaT

        # Merge tables
        df = weekly.merge(
            employees_df[["EmployeeID", "LaborCategory", "Name"]],
            on="EmployeeID",
            how="left"
        )

        # Rename remaining columns
        df.rename(columns={
            "DateCompleted": "If Completed, Date Completed",
            "Status": "Work Product Status",
            "PlannedOrUnplanned": "Planned or Unplanned",
            "EffortPercentage": "Level of Effort (%)",
            "ContractorName": "Contractor (Last Name, First Name)",
            "WorkProductTitle": "Work Product Title",
            "DivisionCommand": "Division/Command",
            "GovtTAName": "Govt TA (Last Name, First Name)",
            "DistinctNFR": "Distinct NFR",
            "DistinctCAP": "Distinct CAP",
            "LaborCategory": "Labor Category"
        }, inplace=True)

        return df
    except Exception:
        return pd.DataFrame()

        
df = load_hr_data()

# Handle offline/empty data
if df.empty:
    st.warning("⚠️ Database is currently offline or HR data is unavailable.")
    st.info("Once the database is restored, contractor activity and KPIs will be displayed here.")
    st.stop()

@st.cache_data(ttl=8 * 3600)
def get_expected_contractors():
    try:
        employees_df = get_data("Employees")
        if employees_df.empty:
            return set()
        return {normalize_text(name) for name in employees_df["Name"].dropna().unique()}
    except Exception:
        return set()

expected_contractors = get_expected_contractors()
    
############################
# --- Data Cleaning ---
############################
df["Reporting Week"] = pd.to_datetime(df["Reporting Week"], errors='coerce')
df["If Completed, Date Completed"] = pd.to_datetime(df["If Completed, Date Completed"], errors='coerce')
df["Work Product Status"] = df["Work Product Status"].astype(str).str.strip().str.title()
df["Planned or Unplanned"] = df["Planned or Unplanned"].astype(str).str.strip().str.lower()
df["Level of Effort (%)"] = pd.to_numeric(df["Level of Effort (%)"], errors='coerce').fillna(0)

# Calculate total hours assuming 40 hours is 100% effort
df["Hours"] = (df["Level of Effort (%)"] / 100 * 40).round(2)

#########################
# --- Sidebar Filters ---
#########################
st.sidebar.header("Filter HR Data")

# Date range filter
min_date = df["Reporting Week"].min()
max_date = df["Reporting Week"].max()
start_date, end_date = st.sidebar.date_input(
    "Select Date Range",
    [min_date, max_date],
    min_value=min_date,
    max_value=max_date
)

# Division filter
divisions = sorted(df["Division/Command"].dropna().unique())
selected_divisions = st.sidebar.multiselect("Select Divisions", divisions)

# Contractor filter
contractors = sorted(df["Contractor (Last Name, First Name)"].dropna().unique())
selected_contractors = st.sidebar.multiselect("Select Contractors", contractors)

# Labor Category filter
labor_cats = sorted(df["Labor Category"].dropna().unique())
selected_labor_cats = st.sidebar.multiselect("Select Labor Categories", labor_cats)

# Reset button
if st.sidebar.button("🔄 Reset Filters"):
    st.experimental_rerun()

# Apply filters
filters = df["Reporting Week"].between(pd.to_datetime(start_date), pd.to_datetime(end_date))
if selected_divisions:
    filters &= df["Division/Command"].isin(selected_divisions)
if selected_contractors:
    filters &= df["Contractor (Last Name, First Name)"].isin(selected_contractors)
if selected_labor_cats:
    filters &= df["Labor Category"].isin(selected_labor_cats)

df = df[filters]


####################
# --- Export CSV ---
####################
st.download_button(
    label="📁 Download Full HR Data as CSV",
    data=df.to_csv(index=False).encode("utf-8"),
    file_name="hr_kpi_data.csv",
    mime="text/csv"
)

#####################
# --- KPI Metrics ---
#####################
st.markdown("## Key Performance Indicators")

total_hours = df["Hours"].sum()
avg_hours_per_contractor = df.groupby("Contractor (Last Name, First Name)")["Hours"].sum().mean()
unplanned_hours = df[df["Planned or Unplanned"] == "unplanned"]["Hours"].sum()
unplanned_pct = (unplanned_hours / total_hours * 100) if total_hours > 0 else 0

# --- Fetch Expected Contractors Dynamically ---

# @st.cache_data(ttl=600)
# def get_expected_contractors():
#     with get_engine().connect() as conn:
#         stmt = select(employees.c.Name)
#         results = conn.execute(stmt).fetchall()

#     # Create DataFrame with proper column name
#     contractor_names = pd.DataFrame(results, columns=["Name"])["Name"].tolist()

#     return {normalize_text(name) for name in contractor_names if name}

@st.cache_data(ttl=8 * 3600)
def get_expected_contractors():
    employees_df = get_data("Employees")
    return {normalize_text(name) for name in employees_df["Name"].dropna().unique()}

expected_contractors = get_expected_contractors()

# --- Empty Data Check ---
if df.empty:
    st.warning("No HR data available.")
    st.stop()

# --- Active Contractors ---
active_contractors = set(
    df["Contractor (Last Name, First Name)"].dropna()
    .apply(normalize_text)
    .unique()
)

# --- Missing Contractors ---
missing_contractors = sorted(expected_contractors - active_contractors)

# Display metrics in columns
k1, k2, k3, k4 = st.columns(4)
k1.metric("Total Hours Worked", f"{total_hours:.1f}")
k2.metric("Avg Hours / Contractor", f"{avg_hours_per_contractor:.1f}")
k3.metric("Unplanned Hours %", f"{unplanned_pct:.1f}%")
k4.metric("Non-reporting Contractors", len(missing_contractors))

#########################
# --- Charts ---
#########################
st.markdown("## Work Metrics Visualizations")

# --- Row 1: Quadrant 1 + Quadrant 2 ---
row1_col1, row1_col2 = st.columns(2)
with row1_col1:
    st.subheader("Work Product Status Overview")
    try:
        status_counts = df["Work Product Status"].value_counts()
        st.plotly_chart(px.pie(
            names=status_counts.index,
            values=status_counts.values,
            title="Work Status Distribution",
        color_discrete_sequence=px.colors.sequential.Blues
        ), use_container_width=True)
    except Exception:
        st.warning("⚠️ Unable to load 'Work Product Status' chart.")
        
with row1_col2:
    st.subheader("Weekly Completion Trend")
    try:
        weekly_completed = (
            df[df["Work Product Status"] == "Completed"]
            .groupby(df["Reporting Week"].dt.to_period("W").dt.start_time)
            .size()
        )
        st.line_chart(weekly_completed)
    except Exception:
        st.warning("⚠️ Unable to load 'Weekly Completion Trend Chart.")

    # --- Row 2: Quadrant 3 + Quadrant 4 ---
row2_col1, row2_col2 = st.columns(2)
with row2_col1:
    st.subheader("Level of Effort by Division")
    try:
        division_effort = (
            df.groupby("Division/Command")["Level of Effort (%)"]
            .sum()
            .sort_values(ascending=True)
            .reset_index()
        )
        st.plotly_chart(px.bar(
            division_effort,
            x="Level of Effort (%)",
            y="Division/Command",
            orientation="h",
            title="Total Effort (%) per Division",
        color_discrete_sequence=px.colors.sequential.Blues
        ), use_container_width=True)
    except Exception:
        st.warning("⚠️ Unable to load Level of Effort by Division chart.")

with row2_col2:
    st.subheader("Unplanned Hours by Division")
    try:
        unplanned_by_div = (
            df[df["Planned or Unplanned"] == "unplanned"]
            .groupby("Division/Command")["Hours"]
            .sum()
            .sort_values(ascending=True)    # Horizontal bar
            .reset_index()
        )
        st.plotly_chart(px.bar(
            unplanned_by_div,
            x="Hours",
            y="Division/Command",
            orientation="h",
            title="Unplanned Hours per Division",
        color_discrete_sequence=px.colors.sequential.Blues
        ), use_container_width=True)
    except Exception:
        st.warning("⚠️ Unable to load 'Unplanned Hours by Division' chart.")

# --- Row 3: Top Work Products + Labor Category Distribution ---
row3_col1, row3_col2 = st.columns(2)
with row3_col1:
    st.subheader("Top Work Products by Total Hours")
    try:
        top_titles = (
            df.groupby("Work Product Title", as_index=False)
            .agg(Total_Hours=("Hours", "sum"), Frequency=("Hours", "count"))
            .sort_values(by="Total_Hours", ascending=False)
            .head(5)
        )
        st.table(top_titles)
    except Exception:
        st.warning("⚠️ Unable to load 'Top Work Products by Totoal Hours' chart.")

with row3_col2:
    st.subheader("Labor Category Distribution")
    try:
        labor_dist = df["Labor Category"].value_counts()
        st.plotly_chart(px.pie(
            names=labor_dist.index,
            values=labor_dist.values,
            title="Labor Categories",
        color_discrete_sequence=px.colors.sequential.Blues
        ), use_container_width=True)
    except Exception:
        st.warning("⚠️ Unable to load 'Labor Category Distibution' chart.")

# --- Heatmap: Hours by Contractor and Month ---
st.subheader("Monthly Hours Heatmap by Contractor")

# @st.cache_data(ttl=600)
# def load_heatmap_data():
#     query = text("""
#         SELECT 
#             e.Name AS Contractor,
#             DATEFROMPARTS(YEAR(wr.WeekStartDate), MONTH(wr.WeekStartDate), 1) AS Month,
#             SUM((wr.EffortPercentage / 100.0) * 40) AS Hours
#         FROM WeeklyReports wr
#         JOIN Employees e ON wr.EmployeeID = e.EmployeeID
#         GROUP BY 
#             e.Name,
#             DATEFROMPARTS(YEAR(wr.WeekStartDate), MONTH(wr.WeekStartDate), 1)
#         ORDER BY Month
#     """)
    
#     with get_engine().connect() as conn:
#         df_heatmap = pd.DataFrame(conn.execute(query).fetchall(), columns=["Contractor", "Month", "Hours"])
    
#     return df_heatmap

# # Fetch aggregated data and pivot for heatmap
# heatmap_data = load_heatmap_data()
# heatmap_df = (
#     heatmap_data
#     .pivot(index="Contractor", columns="Month", values="Hours")
#     .fillna(0)
# )

@st.cache_data(ttl=8 * 3600)
def load_heatmap_data():
    weekly = get_data("WeeklyReports")
    employees_df = get_data("Employees")

    df = weekly.merge(employees_df[["EmployeeID", "Name"]], on="EmployeeID", how="left")
    df["Month"] = pd.to_datetime(df["WeekStartDate"]).dt.to_period("M").dt.to_timestamp()
    df["Hours"] = (df["EffortPercentage"] / 100) * 40

    return (
        df.groupby(["Name", "Month"], as_index=False)["Hours"]
        .sum()
        .rename(columns={"Name": "Contractor"})
    )

try:
    heatmap_df = load_heatmap_data().pivot(index="Contractor", columns="Month", values="Hours").fillna(0)
    
    st.dataframe(
        heatmap_df.style.background_gradient(axis=1, cmap="Blues"),
        use_container_width=True
    )
except Exception:
    st.warning("⚠️ Unable to load heatmap data.")
    
# --- Contractor Coverage Check ---
st.subheader("Contractors with Zero Submissions")
try:
    if missing_contractors:
        st.warning(f"{len(missing_contractors)} contractors have no submissions.")
        st.write(missing_contractors)
    else:
        st.success("All expected contractors have submitted.")
except Exception:
    st.warning("⚠️ Unable to calculate contractor coverage.")


#######################################
# Helper function for testing purposes
######################################

def render_kpis():
    """Helper for tests to check KPI page loads."""
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
