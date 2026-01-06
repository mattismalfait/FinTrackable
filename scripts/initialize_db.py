import os
from dotenv import load_dotenv
from supabase import create_client

# Load environment variables
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("Error: SUPABASE_URL or SUPABASE_KEY not found in .env")
    exit(1)

client = create_client(SUPABASE_URL, SUPABASE_KEY)

def init_users_table():
    try:
        # Check if table exists by trying to select from it
        client.table("user").select("id").limit(1).execute()
        print("Table 'user' already exists.")
    except Exception as e:
        print(f"Checking 'user' table... (Might need manual creation if the following fails)")
        
        print("Please ensure the 'user' table exists in your Supabase project.")
        print("SQL to run in Supabase SQL Editor:")
        print("""
        CREATE TABLE IF NOT EXISTS public.user (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            email TEXT UNIQUE NOT NULL,
            first_name TEXT,
            second_name TEXT,
            created_at TIMESTAMPTZ DEFAULT now()
        );
        """)

if __name__ == "__main__":
    init_users_table()
