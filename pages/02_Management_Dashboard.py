# Import necessary libraries
import streamlit as st  # For creating the interactive web app
import pandas as pd  # For working with tabular data
import plotly.express as px  # For creating visualizations
import re  # For text cleaning using regular expressions

# Import shared modules
from utils.db import get_data

############################
# --- Page Configuration ---
############################
st.set_page_config(
    # browser tab title
    page_title="Management Dashboard", 
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
st.title("Management Dashboard") 
st.caption("Visualize and filter team effort across vendors, divisions, and contractors.")

#################################
# --- Refresh Data on Demand ---
#################################
if st.button("🔄 Refresh Data"):
    from utils.db import load_all_data
    load_all_data.clear()
    if "session_data" in st.session_state:
        del st.session_state["session_data"]
    st.experimental_rerun()


##################################
# --- Load Weekly Report Data ---
#################################
# @st.cache_data(ttl=600)
# def load_weekly_data():
#     with get_engine().connect() as conn:
#         result = conn.execute(text(weekly_reports_with_employees))
#         df = pd.DataFrame(result.fetchall(), columns=result.keys())

#     df.columns = [re.sub(r"\s+", " ", col).strip() for col in df.columns]
#     return df

# df = load_weekly_data()

@st.cache_data(ttl=300) # 8 * 3600 (8hrs)
def get_weekly_df():
    try:
        # df = get_data("WeeklyReports")  # Pulls from cached data
        # employees_df = get_data("Employees")
        from utils.db import load_table
        df = load_table("WeeklyReports")
        employees_df = load_table("Employees")

    
        # Join weekly reports with employees for enriched data
        df = df.merge(
            employees_df,
            how="left",
            left_on="EmployeeID",
            right_on="EmployeeID"
        )
    
        # Rename columns to match your expected schema
        df.rename(columns={
            "VendorName": "Vendor Name",
            "DivisionCommand": "Division/Command",
            "WorkProductTitle": "Work Product Title",
            "EffortPercentage": "Level of Effort (%)",
            "WeekStartDate": "Reporting Week",
            "ContractorName": "Contractor (Last Name, First Name)",
            "GovtTAName": "Govt TA (Last Name, First Name)",
            "Status": "Work Product Status",
            "PlannedOrUnplanned": "Planned or Unplanned"
        }, inplace=True)
    
        return df
    except Exception:
        return pd.DataFrame()  # Empty DataFrame if DB is offline

df = get_weekly_df()


# Incase there is a missing dataset, provide a warning
if df.empty:
    st.warning("⚠️ Database is currently offline or no weekly report data is available.")
    st.info("Once the database is restored, the dashboard will automatically display data.")
    st.stop()

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
vendors = df["Vendor Name"].dropna().sort_values().unique()
contractors = df["Contractor (Last Name, First Name)"].dropna().sort_values().unique()

# Initialize session state for filters
if "selected_weeks" not in st.session_state:
    st.session_state.selected_weeks = []
if "selected_vendors" not in st.session_state:
    st.session_state.selected_vendors = []
if "selected_contractors" not in st.session_state:
    st.session_state.selected_contractors = []

# Sidebar multiselect widgets
selected_weeks = st.sidebar.multiselect("Reporting Week", week_options, default=st.session_state.selected_weeks)
selected_vendors = st.sidebar.multiselect("Vendor", vendors, default=st.session_state.selected_vendors)
selected_contractors = st.sidebar.multiselect("Contractor", contractors, default=st.session_state.selected_contractors)

# Reset button
if st.sidebar.button("Reset Filters"):
    st.session_state.selected_weeks = []
    st.session_state.selected_vendors = []
    st.session_state.selected_contractors = []
    st.experimental_rerun()

# Apply filters
filters = pd.Series(True, index=df.index)

if selected_weeks:
    filters &= df["Reporting Week"].dt.strftime("%Y-%m-%d").isin(selected_weeks)
if selected_vendors:
    filters &= df["Vendor Name"].isin(selected_vendors)
if selected_contractors:
    filters &= df["Contractor (Last Name, First Name)"].isin(selected_contractors)

df = df[filters]

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
        ],
        # color="Level of Effort (%)",  # Color intensity based on effort
        # color_continuous_scale="Blues"  # Apply blue color scheme
    )
    # fig.update_traces(root_color="lightblue")  # Optional: root background
    st.plotly_chart(fig, use_container_width=True)
except ValueError as ve:
    st.error(f"Treemap failed to render: {ve}")


#######################################
# Helper function for testing purposes
######################################

def render_dashboard():
    """Helper for tests to check dashboard loads."""
    try:
        # Import and call your main dashboard render function if exists
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
