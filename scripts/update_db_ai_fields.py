"""
Migration script to add AI metadata columns to the transactions table in Supabase.
"""
import os
import sys
from dotenv import load_dotenv
from supabase import create_client, Client

# Add root directory to path to import config
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database.connection import get_supabase_client

def migrate():
    client = get_supabase_client()
    if not client:
        print("❌ Could not connect to Supabase.")
        return

    print("🚀 Starting migration...")
    
    try:
        # Supabase Python SDK doesn't support direct ALTER TABLE via query() easily without raw SQL access
        # which is often restricted. We'll try to use the rpc() if available or just guide the user.
        # Most users use the SQL editor for schema changes.
        
        sql = """
        ALTER TABLE public.transactions 
        ADD COLUMN IF NOT EXISTS ai_name text,
        ADD COLUMN IF NOT EXISTS ai_reasoning text,
        ADD COLUMN IF NOT EXISTS ai_confidence numeric,
        ADD COLUMN IF NOT EXISTS ai_category text;
        """
        
        print("Please run the following SQL in your Supabase SQL Editor:")
        print("-" * 40)
        print(sql)
        print("-" * 40)
        
        # We can't easily execute raw SQL via the client unless there's a specific RPC
        # So we'll provide this as a utility script for the user or for us to point to.
        
    except Exception as e:
        print(f"❌ Migration failed: {str(e)}")

if __name__ == "__main__":
    migrate()
