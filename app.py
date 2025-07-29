# Import the Streamlit library, to build the interactive web apps
import streamlit as st

#############################
# --- Page Configuration ---
#############################
# Set the title of the browser tab, expand the sidebar, and use a wide layout
st.set_page_config(
    # browser tab title
    page_title="Team Performance Tracker",
    # wide layout for more screen space
    layout="wide",
    # sidebar is expanded by default
    initial_sidebar_state="expanded"
)


#######################
# --- Logo Display ---
#######################
# Display logo at top of app (ensure image path points to valid directory)
st.image("images/Iberia-Advisory.png", width=250)


####################################
# --- Page Title and Description ---
####################################
# Display the main title and a short description below it
st.title("Team Performance Tracker")
st.caption("A centralized tool for monitoring team contributions and workstream alignment at Iberia.")

######################
# --- Main Layout ---
######################
# Create two columns on the page with a width ratio of 1:2 and some spacing between them
col1, col2 = st.columns([1, 2], gap="large")

# --- Left Column: Quick Navigation Section ---
with col1:
    st.subheader("Quick Navigation")

    # Optional: Uncomment if using streamlit >=1.25 and multipage setup
    # st.page_link("01_Form_Submission.py", label="Submit Weekly Report")
    # st.page_link("02_Dashboard.py", label="Management Dashboard")
    # st.page_link("03_HR_KPIs.py", label="HR Metrics & Heatmaps")

    # Display a list of actions users can take, explained in bullet points
    st.markdown("""
    - **Submit Reports**: Log contractor contributions.
    - **View Reports**: Analyze weekly reports.
    - **Track Workstreams**: Overview of team distribution.
    - **Export Data**: Download reports for sharing.
    """)

    # Info box that hints users to use the sidebar for navigating pages
    st.info("Use the **sidebar** to navigate between pages.")

# --- Right Column: App Overview and Instructions ---
with col2:
    # Section header for app explanation with collapsible box
    st.subheader("What This App Does")
    with st.expander("Overview", expanded=True):
        st.markdown("""
        **Iberia’s Team Performance Tracker** helps you:

        - Monitor contributions across teams and vendors.
        - Track effort level, deliverables, and timelines.
        - Identify bottlenecks or underreported areas.
        - Centralize accomplishments and outputs for leadership reporting.
        """)
    
    # Beginner-friendly instructions with collapsible box 
    with st.expander("Getting Started"):
        st.markdown("""
        1. Use the **sidebar** to select an action.
        2. Start by submitting a report or viewing the dashboard.
        3. Filter and explore performance metrics.
        4. Export reports for external stakeholders if needed.
        """)

#################        
# --- Footer ---
#################

# Horizontal line for visual separation
st.markdown("---")
# Friendly footer message
st.caption("Built with ❤️ by the Iberia BackOffice Team.")

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
