"""
Supabase database connection management.
"""

from supabase import create_client, Client
from config.settings import SUPABASE_URL, SUPABASE_KEY
import streamlit as st
from typing import Optional

def get_supabase_client() -> Optional[Client]:
    """
    Get or create a Supabase client instance.
    
    Returns:
        Client: Supabase client instance or None if configuration is missing
    """
    if not SUPABASE_URL or not SUPABASE_KEY:
        st.error("⚠️ Supabase configuration is missing. Please set SUPABASE_URL and SUPABASE_KEY in your .env file.")
        return None
    
    try:
        client = create_client(SUPABASE_URL, SUPABASE_KEY)
        return client
    except Exception as e:
        st.error(f"❌ Failed to connect to Supabase: {str(e)}")
        return None

def test_connection() -> bool:
    """
    Test the Supabase connection.
    
    Returns:
        bool: True if connection is successful, False otherwise
    """
    client = get_supabase_client()
    if not client:
        return False
    
    try:
        # Try a simple query to verify connection
        client.table('transactions').select('id').limit(1).execute()
        return True
    except Exception as e:
        st.error(f"❌ Database connection test failed: {str(e)}")
        return False
