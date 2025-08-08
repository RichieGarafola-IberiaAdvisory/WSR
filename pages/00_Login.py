# pages/00_Login.py
import streamlit as st
from utils.auth import login_form, account_box, logout

st.set_page_config(page_title="Login", layout="centered")

st.title("Team Performance Tracker Login")

# If already logged in, show account info + quick links
if st.session_state.get("authenticated"):
    account_box()  # shows user name/role + logout
    st.success("You’re already signed in.")

    st.markdown("### Quick links")
    # Use page_link if you’re on Streamlit 1.25+
    try:
        st.page_link("pages/01_Form_Submission.py", label="Submit Weekly Report")
        st.page_link("pages/02_Management_Dashboard.py", label="Management Dashboard")
        st.page_link("pages/03_HR_KPIs.py", label="HR KPIs")
        st.page_link("pages/04_Accomplishments_Dashboard.py", label="Accomplishments Dashboard")
    except Exception:
        st.write("Use the sidebar to navigate to other pages.")

    st.divider()
    if st.button("Logout"):
        logout()
        st.rerun()

else:
    # Not logged in: show the login form
    login_form()

    st.info("Use your work email and password. If you don’t have an account, contact an admin.")
