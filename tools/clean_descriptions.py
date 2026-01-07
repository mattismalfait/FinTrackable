"""
Migration script to clean existing transaction descriptions in the database.
Removes redundant payment method text from all existing transactions.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.operations import DatabaseOperations
from utils.text_cleaner import clean_transaction_description
from views.auth import get_current_user
import streamlit as st

def clean_all_descriptions():
    """Clean descriptions for all transactions in the database."""
    
    st.title("🧹 Database Schoonmaak - Omschrijvingen")
    st.write("Dit script verwijdert overtollige tekst uit alle transactie omschrijvingen.")
    
    user = get_current_user()
    if not user:
        st.error("Je moet ingelogd zijn om dit script uit te voeren")
        return
    
    db_ops = DatabaseOperations()
    
    # Get all transactions
    st.info("Transacties ophalen...")
    all_transactions = db_ops.get_transactions(user.id, is_confirmed=None)
    
    if not all_transactions:
        st.warning("Geen transacties gevonden")
        return
    
    st.write(f"**{len(all_transactions)}** transacties gevonden")
    
    # Preview cleaning
    st.subheader("📋 Voorbeeld")
    preview_count = min(5, len(all_transactions))
    for i, trans in enumerate(all_transactions[:preview_count]):
        original = trans.get('omschrijving', '')
        if original:
            cleaned = clean_transaction_description(original)
            if original != cleaned:
                col1, col2 = st.columns(2)
                with col1:
                    st.caption("Voor:")
                    st.text(original)
                with col2:
                    st.caption("Na:")
                    st.text(cleaned)
                st.divider()
    
    # Confirm action
    st.warning("⚠️ Dit zal alle omschrijvingen in de database wijzigen. Deze actie kan niet ongedaan gemaakt worden.")
    
    if st.button("🚀 Start Schoonmaak", type="primary"):
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        updated_count = 0
        skipped_count = 0
        
        for idx, trans in enumerate(all_transactions):
            trans_id = trans['id']
            original_desc = trans.get('omschrijving', '')
            
            if original_desc:
                cleaned_desc = clean_transaction_description(original_desc)
                
                if original_desc != cleaned_desc:
                    # Update in database
                    updates = {"omschrijving": cleaned_desc}
                    if db_ops.update_transaction(trans_id, updates, user.id):
                        updated_count += 1
                    else:
                        st.error(f"Fout bij updaten van transactie {trans_id}")
                else:
                    skipped_count += 1
            else:
                skipped_count += 1
            
            # Update progress
            progress = (idx + 1) / len(all_transactions)
            progress_bar.progress(progress)
            status_text.text(f"Verwerkt: {idx + 1}/{len(all_transactions)}")
        
        st.success(f"✅ Klaar! {updated_count} omschrijvingen bijgewerkt, {skipped_count} overgeslagen")

if __name__ == "__main__":
    clean_all_descriptions()
