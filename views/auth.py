import streamlit as st
from collections import namedtuple

# Simple user model
User = namedtuple('User', ['id', 'email'])

# Fixed user ID for single-user application (matches database owner ID)
FIXED_USER_ID = "f3603492-1261-49bc-aa6b-c8633b48fa61"

# Simple user credentials (plaintext for now)
USERS = {
    "malfait.mattis@gmail.com": "pfUwTc9008!"
}

def show_auth_page():
    """Display simple login page."""
    
    st.title("🏦 FinTrackable")
    st.subheader("Financiële Administratie Geautomatiseerd")
    
    show_login_form()

def show_login_form():
    """Display simple login form."""
    
    with st.form("login_form"):
        email = st.text_input("E-mail")
        password = st.text_input("Wachtwoord", type="password")
        submit = st.form_submit_button("Inloggen")
        
        if submit:
            if not email or not password:
                st.error("Vul alle velden in")
                return
            
            # Simple plaintext authentication
            if email in USERS and USERS[email] == password:
                # Create a simple user object
                st.session_state['user'] = User(id=FIXED_USER_ID, email=email)
                st.success("✅ Succesvol ingelogd!")
                st.rerun()
            else:
                st.error("Ongeldige inloggegevens")

def logout():
    """Handle user logout."""
    # Clear session state
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    
    st.rerun()

def get_current_user():
    """
    Get current logged-in user.
    
    Returns:
        User object or None
    """
    user = st.session_state.get('user', None)
    if isinstance(user, dict):
        # Auto-migrate dictionary to User namedtuple
        user = User(id=user.get('id'), email=user.get('email'))
        st.session_state['user'] = user
    return user

def is_authenticated() -> bool:
    """
    Check if user is authenticated.
    
    Returns:
        bool: True if user is logged in
    """
    return 'user' in st.session_state and st.session_state['user'] is not None
