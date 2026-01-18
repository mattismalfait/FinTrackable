import sys
import os
sys.path.append(os.getcwd())
import pandas as pd
from database.operations import DatabaseOperations
from dotenv import load_dotenv
from decimal import Decimal

load_dotenv()

def analyze_investments():
    db = DatabaseOperations()
    # Use a dummy user_id if we don't have one, but usually it's 'default-user' or retrieved from session
    # For this diagnostic, we'll try to find any transactions.
    # We need the real user_id. Let's try to get it from the DB or just list all if possible.
    # In this app, user_id is usually a UUID from Supabase Auth.
    
    # Let's try to find a user_id first by looking at any transaction
    # Since I don't know the user_id, I'll try to fetch all transactions without filtering if possible, 
    # but the API usually requires user_id.
    
    # Wait, I can look at the .env file to see if there's a test user or something? No.
    # I'll try to get all transactions from the db directly using the client.
    from database.connection import get_supabase_client
    supabase = get_supabase_client()
    
    if not supabase:
        print("Error: Could not connect to Supabase.")
        return

    # Fetch all transactions from the table
    response = supabase.table('transactions').select('*').execute()
    
    if not response.data:
        print("No transactions found in database.")
        return
        
    df = pd.DataFrame(response.data)
    
    # Fetch category names to map IDs
    cat_response = supabase.table('categories').select('id, name').execute()
    cat_map = {c['id']: c['name'] for c in cat_response.data}
    
    # Map category names
    df['category_name'] = df['categorie_id'].map(cat_map).fillna('Overig')
    
    # Filter for confirmed, not lopende, and 'Investeren'
    inv_df = df[
        (df['is_confirmed'] == True) & 
        (df['is_lopende_rekening'] == False) & 
        (df['category_name'] == 'Investeren')
    ].copy()
    
    inv_df['bedrag'] = pd.to_numeric(inv_df['bedrag'])
    
    print(f"--- Investments Analysis ---")
    print(f"Total Transactions in 'Investeren': {len(inv_df)}")
    print(f"Sum of amounts: {inv_df['bedrag'].sum()}")
    print(f"Absolute sum: {inv_df['bedrag'].abs().sum()}")
    print(f"Net sum (current app logic): {abs(inv_df['bedrag'].sum())}")
    print("\nDetailed Transactions:")
    pd.set_option('display.max_colwidth', None)
    pd.set_option('display.max_rows', None)
    pd.set_option('display.width', 1000)
    details = inv_df[['datum', 'naam_tegenpartij', 'bedrag', 'omschrijving']].to_string(index=False)
    print(details)
    
    with open('investment_details.txt', 'w', encoding='utf-8') as f:
        f.write(details)
    print(f"\nFull details saved to investment_details.txt")

if __name__ == "__main__":
    analyze_investments()
