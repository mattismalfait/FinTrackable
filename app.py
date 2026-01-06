"""
FinTrackable - Financial Administration Application
Main Streamlit application entry point.
"""

import streamlit as st
from views.auth import show_auth_page, is_authenticated, logout
from views.dashboard import show_dashboard
from views.upload import show_upload_page
from views.categorization_review import show_categorization_review
from database.connection import get_supabase_client

from utils.ui.template_loader import load_template

# Page configuration
st.set_page_config(
    page_title="FinTrackable - Financiële Administratie",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load and apply premium CSS
main_css = load_template("css/main.css")
st.markdown(f"<style>{main_css}</style>", unsafe_allow_html=True)

def main():
    """Main application function."""
    
    # Check if Supabase is configured
    client = get_supabase_client()
    if not client:
        st.error("⚠️ Supabase is niet geconfigureerd. Controleer je .env bestand.")
        st.info("""
        **Setup instructies:**
        
        1. Kopieer `.env.example` naar `.env`
        2. Vul je Supabase credentials in:
           - `SUPABASE_URL`: Je Supabase project URL
           - `SUPABASE_KEY`: Je Supabase anon/public key
        3. Herstart de applicatie
        """)
        return
    
    # Check authentication
    if not is_authenticated():
        show_auth_page()
        return
    
    # User is authenticated - show main application
    show_main_app()

def show_main_app():
    """Show main application with navigation."""
    
    # Sidebar navigation
    with st.sidebar:
        st.title("🏦 FinTrackable")
        st.markdown("---")
        
        # Navigation menu
        page = st.radio(
            "Navigatie",
            ["📊 Dashboard", "📤 CSV Importeren", "🏷️ Categorieën", "⚙️ Instellingen"],
            key="navigation"
        )
        
        st.markdown("---")
        
        # Logout button
        if st.button("🚪 Uitloggen", use_container_width=True):
            logout()
    
    # Page routing
    if page == "📊 Dashboard":
        show_dashboard()
    elif page == "📤 CSV Importeren":
        show_upload_page()
    elif page == "🏷️ Categorieën":
        show_categorization_review()
    elif page == "⚙️ Instellingen":
        show_settings_page()

def show_settings_page():
    """Show settings and preferences page."""
    
    st.title("⚙️ Instellingen")
    
    from ui.auth import get_current_user
    from database.operations import DatabaseOperations
    
    user = get_current_user()
    if not user:
        return
    
    db_ops = DatabaseOperations()
    preferences = db_ops.get_user_preferences(user.id)
    
    st.subheader("Gebruikersvoorkeuren")
    
    # Investment goal setting
    current_goal = preferences['investment_goal_percentage'] if preferences else 20.0
    
    with st.form("preferences_form"):
        investment_goal = st.slider(
            "Investeringsdoel (%)",
            min_value=0.0,
            max_value=100.0,
            value=float(current_goal),
            step=1.0,
            help="Het percentage van je inkomen dat je wilt investeren"
        )
        
        submit = st.form_submit_button("💾 Opslaan")
        
        if submit:
            success = db_ops.create_or_update_preferences(
                user.id,
                {"investment_goal_percentage": investment_goal}
            )
            if success:
                st.success("✅ Voorkeuren opgeslagen!")
                st.rerun()
            else:
                st.error("❌ Fout bij opslaan van voorkeuren")
    
    st.divider()
    
    # Account information
    st.subheader("Account Informatie")
    st.write(f"**E-mail:** {user.email}")
    st.write(f"**Gebruikers ID:** {user.id}")
    
    st.divider()
    
    # Danger zone
    st.subheader("⚠️ Gevaarlijke Acties")
    
    with st.expander("Alle transacties verwijderen", expanded=False):
        st.warning("⚠️ Deze actie kan niet ongedaan worden gemaakt!")
        
        if st.button("🗑️ Verwijder alle transacties", type="secondary"):
            # Confirmation
            st.session_state['confirm_delete'] = True
        
        if st.session_state.get('confirm_delete', False):
            st.error("Ben je zeker? Dit verwijdert ALLE transacties permanent!")
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("✅ Ja, verwijder alles", type="primary"):
                    success = db_ops.delete_all_transactions(user.id)
                    if success:
                        st.success("✅ Alle transacties verwijderd")
                        st.session_state['confirm_delete'] = False
                        st.rerun()
                    else:
                        st.error("❌ Fout bij verwijderen")
            
            with col2:
                if st.button("❌ Annuleren"):
                    st.session_state['confirm_delete'] = False
                    st.rerun()

if __name__ == "__main__":
    main()
