import streamlit as st
import hashlib
from sqlalchemy import text
from utils.db import get_engine

# ----------------------------
# Helpers
# ----------------------------
def _hash_password(raw_password: str) -> str:
    """Hash plain text password using SHA‑256."""
    return hashlib.sha256(raw_password.encode("utf-8")).hexdigest()

def _get_user_by_email(email: str):
    """
    Fetch a single roster record by email.
    Avoids loading all rows into memory.
    """
    with get_engine().connect() as conn:
        result = conn.execute(
            text("""
                SELECT TOP 1 
                    RosterID, EmployeeID, Email, FirstName, LastName,
                    Role, Organization, ProjectName, PasswordHash
                FROM Roster
                WHERE LOWER(Email) = LOWER(:email)
            """),
            {"email": email}
        ).mappings().first()
    return result

# ----------------------------
# Auth Core
# ----------------------------
def authenticate(email: str, password: str) -> bool:
    """
    Authenticate user by email + password.
    Stores auth/session metadata in st.session_state if valid.
    """
    user = _get_user_by_email(email)
    if not user:
        return False

    if (user.get("PasswordHash") or "") != _hash_password(password):
        return False

    # Store relevant info in session
    st.session_state.authenticated = True
    st.session_state.user_email = user["Email"]
    st.session_state.user_name = f"{user['FirstName']} {user['LastName']}".strip()
    st.session_state.user_role = (user.get("Role") or "user").lower()
    st.session_state.user_id = int(user["RosterID"])
    st.session_state.organization = user.get("Organization") or ""
    st.session_state.project = user.get("ProjectName") or ""

    return True

def logout():
    """Remove all auth‑related keys from session state."""
    for key in list(st.session_state.keys()):
        if key.startswith("user_") or key in {"authenticated", "organization", "project"}:
            del st.session_state[key]

def require_login():
    """Stop page execution if user is not logged in."""
    if not st.session_state.get("authenticated"):
        st.error("🔐 You must be logged in to access this page.")
        st.stop()

def require_role(roles: list[str]):
    """Stop execution if logged in user lacks required role(s)."""
    require_login()
    role = st.session_state.get("user_role", "").lower()
    if role not in [r.lower() for r in roles]:
        st.error("⛔ You do not have permission to access this content.")
        st.stop()

# ----------------------------
# UI Widget
# ----------------------------
def login_form():
    """Display the login form UI."""
    with st.form("login_form"):
        st.subheader("🔐 Secure Login")
        email = st.text_input("Work Email")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")

        if submitted:
            if authenticate(email, password):
                st.success(f"Welcome {st.session_state.user_name}!")
                st.rerun()
            else:
                st.error("Invalid credentials. Please check your email and password.")

def account_box():
    with st.sidebar:
        if st.session_state.get("authenticated"):
            st.markdown(
                f"**{st.session_state.user_name}**  \n"
                f"`{st.session_state.user_role}`  \n"
                f"{st.session_state.get('organization','')}"
            )
            if st.button("Logout"):
                logout()
                st.rerun()

