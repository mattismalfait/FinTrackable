import streamlit as st
from collections import namedtuple

# Simple user model for consistent dot-notation access
User = namedtuple('User', ['id', 'email', 'first_name', 'second_name'])

# This is the primary UUID associated with existing transactions in Supabase
FIXED_USER_ID = "f3603492-1261-49bc-aa6b-c8633b48fa61"

# Simplified user list for easy access
USERS = {
    "malfait.mattis@gmail.com": {
        "password": "pfUwTc9008!",
        "first_name": "Mattis",
        "second_name": "Malfait",
        "id": FIXED_USER_ID
    }
}

def show_auth_page():
    """Display the premium authentication page."""
    from utils.ui.template_loader import load_template
    
    # We render the login template which includes our base layout
    html = load_template("login.html")
    import re
    minified = re.sub(r'\s+', ' ', html).strip()
    st.markdown(minified, unsafe_allow_html=True)
    
    # Real functional Streamlit form
    with st.container():
        st.markdown("<br><br>", unsafe_allow_html=True)
        tab_login, tab_signup = st.tabs([" Login to Dashboard", " Register new account"])
        
        with tab_login:
            show_login_form()
            
        with tab_signup:
            show_signup_form()

def show_login_form():
    """Display login form."""
    with st.form("login_form"):
        email = st.text_input("E-mail")
        password = st.text_input("Wachtwoord", type="password")
        submit = st.form_submit_button("Inloggen", use_container_width=True)
        
        if submit:
            if not email or not password:
                st.error("Vul alle velden in")
                return
                
            from database.operations import DatabaseOperations
            db_ops = DatabaseOperations()
            
            user_record = db_ops.get_user_by_email(email)
            if user_record and user_record.get('password') == password:
                st.session_state['user'] = User(
                    id=user_record["id"],
                    email=user_record["email"],
                    first_name=user_record["first_name"],
                    second_name=user_record["second_name"]
                )
                st.success(" Succesvol ingelogd!")
                st.rerun()
            else:
                st.error("Ongeldige e-mail of wachtwoord.")

def show_signup_form():
    """Display registration form."""
    with st.form("signup_form"):
        col1, col2 = st.columns(2)
        with col1:
            first_name = st.text_input("Voornaam")
        with col2:
            second_name = st.text_input("Achternaam")
            
        email = st.text_input("E-mail")
        password = st.text_input("Wachtwoord", type="password")
        confirm_password = st.text_input("Bevestig Wachtwoord", type="password")
        
        submit = st.form_submit_button("Account Aanmaken", use_container_width=True)
        
        if submit:
            if not all([first_name, second_name, email, password]):
                st.error("Vul alle velden in")
                return
            
            if password != confirm_password:
                st.error("Wachtwoorden komen niet overeen")
                return
            
            from database.operations import DatabaseOperations
            db_ops = DatabaseOperations()
            
            user_record, error = db_ops.create_user(email, password, first_name, second_name)
            
            if error:
                st.error(error)
            else:
                st.session_state['user'] = User(
                    id=user_record["id"],
                    email=user_record["email"],
                    first_name=user_record["first_name"],
                    second_name=user_record["second_name"]
                )
                st.success(" Account succesvol aangemaakt!")
                st.rerun()

def logout():
    """Handle user logout."""
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

def get_current_user():
    """
    Get current logged-in user.
    Always returns a User object (namedtuple) for consistency.
    """
    user = st.session_state.get('user', None)
    
    # Object fixation & migration
    if user and (isinstance(user, dict) or not hasattr(user, 'first_name')):
        if isinstance(user, dict):
            u_id = user.get('id', FIXED_USER_ID)
            u_email = user.get('email', '')
            u_first = user.get('first_name', 'User')
            u_second = user.get('second_name', '')
        else:
            u_id = user.id
            u_email = user.email
            u_first = getattr(user, 'first_name', getattr(user, 'name', 'User').split(' ')[0])
            u_second = getattr(user, 'second_name', ' '.join(getattr(user, 'name', 'User').split(' ')[1:]))
            
        user = User(id=u_id, email=u_email, first_name=u_first, second_name=u_second)
        st.session_state['user'] = user
        
    return user

def is_authenticated() -> bool:
    """Check if user is authenticated."""
    return 'user' in st.session_state and st.session_state['user'] is not None
