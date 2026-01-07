
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("Error: credentials missing")
    exit(1)

client = create_client(SUPABASE_URL, SUPABASE_KEY)

# SQL to add column safely
sql = """
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'transactions' AND column_name = 'is_lopende_rekening') THEN
        ALTER TABLE transactions ADD COLUMN is_lopende_rekening BOOLEAN DEFAULT FALSE;
    END IF;
END
$$;
"""

try:
    # Attempt to execute raw SQL if possible via rpc or just try to use a method if available. 
    # Standard supabase-py client doesn't expose raw SQL easily unless there is a saved function.
    # We will try to rely on a 'exec_sql' function if it exists, or just use PostgREST if we can.
    # Since we can't easily run DDL via the standard client without a helper function on the server,
    # I will assume I might fail here if I don't have a helper.
    # However, for this environment, let's try to notify user if we can't.
    # BUT, actually, standard workaround:
    
    # We will try to just run it. If this fails, I'll ask the user.
    # Actually, as an AI, I know that Supabase-py doesn't do raw SQL well without a function.
    # I will create a function via the SQL editor? No, I can't access that.
    
    # Wait, usually `client.postgrest.rpc(...)` is used.
    # If the user hasn't set up an `exec_sql` function, I can't do this.
    
    print("Cannot run raw DDL from python client without a helper RPC.")
    print("Please execute this SQL in your Supabase Dashboard SQL Editor:")
    print("ALTER TABLE transactions ADD COLUMN IF NOT EXISTS is_lopende_rekening BOOLEAN DEFAULT FALSE;")
    
except Exception as e:
    print(f"Error: {e}")
