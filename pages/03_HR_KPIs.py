# Import required libraries
import streamlit as st  # Used for building the web app
from sqlalchemy import select, join  # For database connections
import pandas as pd  # For working with tabular data
import plotly.express as px  # For generating interactive charts


from utils.db import get_engine, employees, weekly_reports
from utils.helpers import normalize_text

############################
# --- Page Configuration ---
############################
st.set_page_config(
    # browser tab title
     page_title="HR Dashboard", 
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
st.title("HR Management Dashboard")
st.caption("Track contractor activity, coverage, and labor category distribution.")

################################
# --- Data Loader ---
################################
# Cache the function output for 10 minutes
@st.cache_data(ttl=600)
def load_hr_data():
    # Join weekly reports and employees on employee ID
    j = join(
        weekly_reports, 
        employees, 
        weekly_reports.c.EmployeeID == employees.c.EmployeeID
    )
    
    stmt = select(
        weekly_reports,
        employees.c.LaborCategory
    ).select_from(j)

    # Execute query and load into DataFrame
    with get_engine().connect() as conn:
        df = pd.DataFrame(conn.execute(stmt).fetchall(), columns=stmt.columns.keys())

    # Rename columns for clarity
    df.rename(columns={
        'WeekStartDate': 'Reporting Week',
        'DateCompleted': 'If Completed, Date Completed',
        'Status': 'Work Product Status',
        'PlannedOrUnplanned': 'Planned or Unplanned',
        'EffortPercentage': 'Level of Effort (%)',
        'ContractorName': 'Contractor (Last Name, First Name)',
        'WorkProductTitle': 'Work Product Title',
        'DivisionCommand': 'Division/Command',
        'GovtTAName': 'Govt TA (Last Name, First Name)',
        'DistinctNFR': 'Distinct NFR',
        'DistinctCAP': 'Distinct CAP',
        'LaborCategory': 'Labor Category'
    }, inplace=True)

    return df

# Load the data
df = load_hr_data()

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

# Define expected contractors manually or from config
expected_contractors = {
    "Wild, Adam", "MacDonald, Alex", "Siddiqui, Ali", "Ma, Annie", "Jones, Ben", "Veit, Beverly", "Verrochi, Brian", "Doherty, Bryn", "Breslin, Casey", "Filer, Chaunoi", "Suriya, David", "Bruzdzinski, Don", "Mehm, Erica", "Fawale, Faith", "Chowdhury, Fazle", "Leitzinger, Jack", "Clack, Jaden", "Freire, Jared", "Clack, Jessie", "Holland, Joe", "Johnson, Jordan", "Good, Kevin", "Blyden, Latisha", "Sabhelhaus, Max", "McKillop, Meghan", "Swinson, Michael", "Hussain, Naveed", "Hart, Peter", "Garafola, Richie", "Thompson, Rob", "Waguespack, Ryan", "Schulze, Terri", "Schafer, Todd", "Javed, Usman", "Corkery, Bill", "Corkery, William", "Derrick, Zachary", "O'Brien, Talia", "Berrio, Yenis"

}

active_contractors = set(df["Contractor (Last Name, First Name)"].dropna().apply(normalize_text).unique())
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
    status_counts = df["Work Product Status"].value_counts()
    st.plotly_chart(px.pie(
        names=status_counts.index,
        values=status_counts.values,
        title="Work Status Distribution"
    ), use_container_width=True)

with row1_col2:
    st.subheader("Weekly Completion Trend")
    weekly_completed = (
        df[df["Work Product Status"] == "Completed"]
        .groupby(df["Reporting Week"].dt.to_period("W").dt.start_time)
        .size()
    )
    st.line_chart(weekly_completed)

    # --- Row 2: Quadrant 3 + Quadrant 4 ---
row2_col1, row2_col2 = st.columns(2)
with row2_col1:
    st.subheader("Level of Effort by Division")
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
        title="Total Effort (%) per Division"
    ), use_container_width=True)

with row2_col2:
    st.subheader("Unplanned Hours by Division")
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
        title="Unplanned Hours per Division"
    ), use_container_width=True)

# --- Row 3: Top Work Products + Labor Category Distribution ---
row3_col1, row3_col2 = st.columns(2)
with row3_col1:
    st.subheader("Top Work Products by Total Hours")
    top_titles = (
        df.groupby("Work Product Title", as_index=False)
        .agg(Total_Hours=("Hours", "sum"), Frequency=("Hours", "count"))
        .sort_values(by="Total_Hours", ascending=False)
        .head(5)
    )
    st.table(top_titles)

with row3_col2:
    st.subheader("Labor Category Distribution")
    labor_dist = df["Labor Category"].value_counts()
    st.plotly_chart(px.pie(
        names=labor_dist.index,
        values=labor_dist.values,
        title="Labor Categories"
    ), use_container_width=True)

# --- Heatmap: Hours by Contractor and Month ---
st.subheader("Monthly Hours Heatmap by Contractor")
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

# --- Contractor Coverage Check --
st.subheader("Contractors with Zero Submissions")
if missing_contractors:
    st.warning(f"{len(missing_contractors)} contractors have no submissions.")
    st.write(missing_contractors)
else:
    st.success("All expected contractors have submitted.")

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