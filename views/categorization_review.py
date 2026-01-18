"""
Transaction categorization review interface.
Allows users to review and correct automated categorizations.
"""

import streamlit as st
from database.operations import DatabaseOperations
from services.categorization import CategorizationEngine
from views.auth import get_current_user
from models.transaction import Transaction
from decimal import Decimal

def show_categorization_review():
    """Display categorization review interface."""
    
    st.title("Categorisatie Beheren")
    
    user = get_current_user()
    if not user:
        st.error("Je moet ingelogd zijn om categorieën te beheren")
        return
    
    db_ops = DatabaseOperations()
    
    # Tabs for different views
    tab1, tab2, tab3 = st.tabs([" Te Bevestigen", " Historiek", " Regels Beheren"])
    
    with tab1:
        show_pending_review(user.id, db_ops)
    
    with tab2:
        show_confirmed_history(user.id, db_ops)
    
    with tab3:
        show_rules_management(user.id, db_ops)

import pandas as pd
from datetime import datetime, date, timedelta

def handle_pending_change(user_id: str, db_ops: DatabaseOperations):
    """Callback for st.data_editor on_change in show_pending_review."""
    state = st.session_state.get("editor_pending")
    if not state or not state.get("edited_rows"):
        return
        
    df = st.session_state.pending_trans_df
    edits = state["edited_rows"]
    
    # Rebuild filtered_df to map positions back to actual indices
    filtered_df = df.copy()
    search_q = st.session_state.get("pending_search")
    cat_f = st.session_state.get("pending_cat_opt")
    
    if search_q:
        q = search_q.lower()
        mask = (
            filtered_df['Tegenpartij'].str.lower().str.contains(q, na=False) |
            filtered_df['Categorie'].str.lower().str.contains(q, na=False) |
            filtered_df['Omschrijving'].str.lower().str.contains(q, na=False) |
            filtered_df['AI Naam'].str.lower().str.contains(q, na=False) |
            filtered_df['AI Motivatie'].str.lower().str.contains(q, na=False)
        )
        filtered_df = filtered_df[mask]
    
    if cat_f and cat_f != "Alle Categorieën":
        filtered_df = filtered_df[filtered_df['Categorie'] == cat_f]

    # We need categories for ID lookup - Cache aware
    if 'user_categories_cache' not in st.session_state:
         st.session_state.user_categories_cache = db_ops.get_categories(user_id)
    user_categories = st.session_state.user_categories_cache
    
    cat_name_to_id = {c['name']: c['id'] for c in user_categories}
    
    for pos_str, changes in edits.items():
        pos = int(pos_str)
        if pos >= len(filtered_df): continue
        
        idx = filtered_df.index[pos]
        row_id = df.at[idx, 'id']
        current_row = df.loc[idx]
        
        # Determine if we should trigger batch category update
        if "Categorie" in changes:
            new_cat_name = changes["Categorie"]
            is_selected = edits.get(pos_str, {}).get("Select", current_row["Select"])
            
            if is_selected:
                c_id = cat_name_to_id.get(new_cat_name)
                # Iterate filtered_df to find other selected rows for visual update
                for other_pos, (other_idx, row) in enumerate(filtered_df.iterrows()):
                    other_pos_str = str(other_pos)
                    other_sel = edits.get(other_pos_str, {}).get("Select", row["Select"])
                    
                    if other_sel and other_idx != idx:
                        if c_id:
                            db_ops.update_transaction(row['id'], {"categorie_id": c_id}, user_id)
                        
                        if other_pos_str not in edits: edits[other_pos_str] = {}
                        edits[other_pos_str]["Categorie"] = new_cat_name

        # Batch Lopende (Current Account) Logic
        if "Lopende" in changes:
            new_val = bool(changes["Lopende"])
            is_selected = edits.get(pos_str, {}).get("Select", current_row["Select"])
            
            if is_selected:
                # Iterate filtered_df to find other selected rows for visual update
                for other_pos, (other_idx, row) in enumerate(filtered_df.iterrows()):
                    other_pos_str = str(other_pos)
                    other_sel = edits.get(other_pos_str, {}).get("Select", row["Select"])
                    
                    if other_sel and other_idx != idx:
                         db_ops.update_transaction(row['id'], {"is_lopende_rekening": new_val}, user_id)
                         # Update session state DF immediately for optimistic UI
                         df.at[other_idx, 'Lopende'] = new_val
                         
                         if other_pos_str not in edits: edits[other_pos_str] = {}
                         edits[other_pos_str]["Lopende"] = new_val

        # Prepare main row update
        cat_val = changes.get("Categorie", current_row["Categorie"])
        c_id = cat_name_to_id.get(cat_val)
        
        # Update session state DF immediately
        if "Select" in changes: df.at[idx, "Select"] = bool(changes["Select"])
        if "Categorie" in changes: df.at[idx, "Categorie"] = cat_val
        if "Lopende" in changes: df.at[idx, "Lopende"] = bool(changes["Lopende"])
        if "Tegenpartij" in changes: df.at[idx, "Tegenpartij"] = str(changes["Tegenpartij"])
        if "Omschrijving" in changes: df.at[idx, "Omschrijving"] = str(changes["Omschrijving"])
        if "Bedrag" in changes: df.at[idx, "Bedrag"] = float(changes["Bedrag"])

        updates = {
            "datum": changes.get("Datum", current_row["Datum"]).isoformat() if hasattr(changes.get("Datum", current_row["Datum"]), "isoformat") else str(changes.get("Datum", current_row["Datum"])),
            "bedrag": float(changes.get("Bedrag", current_row["Bedrag"])),
            "naam_tegenpartij": str(changes.get("Tegenpartij", current_row["Tegenpartij"])),
            "omschrijving": str(changes.get("Omschrijving", current_row["Omschrijving"])),
            "categorie_id": c_id,
            "is_lopende_rekening": bool(changes.get("Lopende", current_row["Lopende"]))
        }
        db_ops.update_transaction(row_id, updates, user_id)

@st.fragment
def show_pending_review(user_id: str, db_ops: DatabaseOperations):
    """Show pending (unconfirmed) transactions review interface."""
    
    # Check for suggested categories
    if 'new_ai_cats' in st.session_state and st.session_state['new_ai_cats']:
        with st.expander(" AI Suggereert Nieuwe Categorieën", expanded=True):
            st.write("De AI heeft transacties gevonden die niet passen in je huidige categorieën.")
            
            cats_to_remove = []
            for i, new_cat in enumerate(st.session_state['new_ai_cats']):
                c1, c2, c3 = st.columns([2, 1, 1])
                with c1:
                    st.write(f"**{new_cat}**")
                with c2:
                    color = st.color_picker("Kleur", "#3b82f6", key=f"new_ai_c_{i}")
                with c3:
                    if st.button("Aanmaken & Toepassen", key=f"btn_create_ai_{i}"):
                        # Create category
                        from models.category import Category
                        cat_obj = Category(name=new_cat, color=color, rules=[
                            {"field": "ai_category", "contains": [new_cat]} # Dummy rule tracking
                        ])
                        new_id = db_ops.create_category(cat_obj, user_id)
                        
                        if new_id:
                            # Update all transactions that have this ai_category
                            if db_ops.client:
                                db_ops.client.table("transactions").update({
                                    "categorie_id": new_id
                                }).eq("user_id", user_id).eq("ai_category", new_cat).execute()
                            
                            st.success(f"Categorie '{new_cat}' aangemaakt en toegepast!")
                            cats_to_remove.append(new_cat)
                            st.session_state.pending_trans_reload = True
                        else:
                            st.error("Kon categorie niet aanmaken.")
            
            if cats_to_remove:
                for c in cats_to_remove:
                    st.session_state['new_ai_cats'].remove(c)
                st.rerun()

            if st.button("Negeer suggesties", type="secondary"):
                del st.session_state['new_ai_cats']
                st.rerun()
                
    st.subheader("Onbevestigde Transacties")
    
    # Initialize reload flag
    if 'pending_trans_reload' not in st.session_state:
        st.session_state.pending_trans_reload = True
        
    # Check if we need to fetch/rebuild
    if 'pending_trans_df' not in st.session_state or st.session_state.pending_trans_reload:
        transactions = db_ops.get_transactions(user_id, is_confirmed=False)
        
        # Get category list and mapping - CACHED
        if 'user_categories_cache' not in st.session_state or st.session_state.pending_trans_reload:
             st.session_state.user_categories_cache = db_ops.get_categories(user_id)
        
        user_categories = st.session_state.user_categories_cache
        
        # STRICTLY use DB categories
        db_category_names = sorted([c['name'] for c in user_categories])
        if "Overig" not in db_category_names:
            db_category_names.append("Overig")
            
        # Convert to DataFrame
        df_data = []
        for t in transactions:
            display_name = t.get('naam_tegenpartij')
            if not display_name or display_name.strip() in ["", "-", "--", "---"]:
                display_name = "Onbekend"
                
            current_category = t.get('categorie', 'Overig')
            if current_category not in db_category_names:
                current_category = "Overig"

            df_data.append({
                "Select": False,
                "Datum": datetime.strptime(t['datum'], '%Y-%m-%d').date() if isinstance(t['datum'], str) else t['datum'],
                "Tegenpartij": display_name,
                "Bedrag": float(t['bedrag']),
                "Categorie": current_category,
                "Lopende": t.get('is_lopende_rekening', False),
                "Omschrijving": t.get('omschrijving', '') or "",
                "AI Naam": t.get('ai_name', ''),
                "AI Motivatie": t.get('ai_reasoning', ''),
                "Vertrouwen": float(t.get('ai_confidence') or 0.0),
                "id": t['id'] # Hidden column
            })


        
        # Convert to DataFrame with predefined columns to avoid KeyError on empty data
        columns = ["Select", "Datum", "Tegenpartij", "Bedrag", "Categorie", "Lopende", "Omschrijving", "AI Naam", "AI Motivatie", "Vertrouwen", "id"]
        if df_data:
            st.session_state.pending_trans_df = pd.DataFrame(df_data)
        else:
            st.session_state.pending_trans_df = pd.DataFrame(columns=columns)
            
        st.session_state.pending_trans_reload = False
        
        # Clear editor state because underlying data changed
        if 'editor_pending' in st.session_state:
            del st.session_state.editor_pending

    # Helpers for Dropdown (Use Cache)
    user_categories = st.session_state.get('user_categories_cache', [])
    # Fallback if cache missing (shouldn't happen if logic above is correct, but safety first)
    if not user_categories:
        user_categories = db_ops.get_categories(user_id)
        st.session_state.user_categories_cache = user_categories

    cat_name_to_id = {c['name']: c['id'] for c in user_categories}
    cat_engine = CategorizationEngine(user_categories)
    db_category_names = sorted([c['name'] for c in user_categories])
    if "Overig" not in db_category_names:
        db_category_names.append("Overig")
        
    #  Search and Filter UI
    st.write(f"**{len(st.session_state.pending_trans_df)}** transacties wachten op bevestiging")
    
    col_search, col_cat_filter = st.columns([3, 1.5])
    with col_search:
        search_query = st.text_input(" Broad Search", placeholder="Zoek op naam, omschrijving, AI details...", key="pending_search", label_visibility="collapsed")
    with col_cat_filter:
        cat_options = ["Alle Categorieën"] + db_category_names
        pending_cat_filter = st.selectbox("Categoriefilter", options=cat_options, key="pending_cat_opt", label_visibility="collapsed")

    # Apply filters
    filtered_df = st.session_state.pending_trans_df.copy()
    if search_query:
        q = search_query.lower()
        mask = (
            filtered_df['Tegenpartij'].str.lower().str.contains(q, na=False) |
            filtered_df['Categorie'].str.lower().str.contains(q, na=False) |
            filtered_df['Omschrijving'].str.lower().str.contains(q, na=False) |
            filtered_df['AI Naam'].str.lower().str.contains(q, na=False) |
            filtered_df['AI Motivatie'].str.lower().str.contains(q, na=False)
        )
        filtered_df = filtered_df[mask]
    
    if pending_cat_filter != "Alle Categorieën":
        filtered_df = filtered_df[filtered_df['Categorie'] == pending_cat_filter]

    if filtered_df.empty:
        st.info("Geen transacties gevonden voor deze filters.")
    
    # Quick Add Category 
    with st.expander(" Nieuwe Categorie Aanmaken", expanded=False):
        c1, c2, c3 = st.columns([3, 1, 1])
        with c1:
            new_cat_quick = st.text_input("Naam nieuwe categorie", key="quick_cat_name", placeholder="Bijv. Hobby's")
        with c2:
            import random
            colors = ["#ef4444", "#f97316", "#f59e0b", "#84cc16", "#10b981", "#06b6d4", "#3b82f6", "#8b5cf6", "#ec4899"]
            new_cat_color_quick = st.color_picker("Kleur", random.choice(colors), key="quick_cat_color")
        with c3:
            st.write("") # Spacer
            if st.button("Toevoegen", key="quick_cat_add"):
                if new_cat_quick:
                    from models.category import Category
                    new_cat_obj = Category(name=new_cat_quick.strip(), color=new_cat_color_quick)
                    if db_ops.create_category(new_cat_obj, user_id):
                        st.success(f"Categorie '{new_cat_quick}' toegevoegd!")
                        st.session_state.pending_trans_reload = True # Reload to update dropdowns
                        if 'user_categories_cache' in st.session_state: del st.session_state.user_categories_cache # Invalidate cache
                        st.rerun()
                    else:
                        st.error("Kon categorie niet aanmaken")
                else:
                    st.warning("Vul een naam in")
            
    # Combined Action Row
    col_confirm, col_delete, col_ai, col_sel_all, col_desel_all = st.columns([1.5, 1.5, 2, 1.5, 1.5])
    
    with col_confirm:
        if st.button("Bevestig", type="primary", use_container_width=True, help="Bevestig de geselecteerde transacties", key="btn_confirm_top"):
            # Use current state of editor if available
            success_count = 0
            # Since the button is above the editor, we rely on the editor key 'editor_pending'
            # which might not have the LATEST edits yet unless on_change was triggered.
            # But the 'Select' checkboxes usually trigger rerun or are captured.
            # We'll use the session state DF which is updated by the on_change callback.
            df_to_proc = st.session_state.pending_trans_df
            for index, row in df_to_proc.iterrows():
                if row['Select']:
                    trans_id = row['id']
                    cat_id = cat_name_to_id.get(row['Categorie'])
                    if cat_id:
                        db_ops.update_transaction(trans_id, {"is_confirmed": True, "categorie_id": cat_id}, user_id)
                        success_count += 1
            
            if success_count > 0:
                st.success(f"{success_count} transacties bevestigd!")
                st.session_state.pending_trans_reload = True
                st.rerun()

    with col_delete:
        if st.button("Verwijder", type="secondary", use_container_width=True, help="Verwijder geselecteerde transacties", key="btn_delete_top"):
            df_to_proc = st.session_state.pending_trans_df
            selected_rows = df_to_proc[df_to_proc["Select"] == True]
            if not selected_rows.empty:
                deleted_count = 0
                for _, row in selected_rows.iterrows():
                    if db_ops.delete_transaction(row['id'], user_id):
                        deleted_count += 1
                if deleted_count > 0:
                    st.success(f"{deleted_count} verwijderd!")
                    st.session_state.pending_trans_reload = True
                    st.rerun()

    with col_ai:
        if st.button("AI Optimaliseer", help="Laat de AI agent betere namen en categorieën voorstellen", use_container_width=True, key="btn_ai_top"):
            df_to_proc = st.session_state.pending_trans_df
            selected_rows = df_to_proc[df_to_proc["Select"] == True]
            if selected_rows.empty:
                st.warning("Selecteer eerst transacties.")
            else:
                from services.ai_categorizer import AiCategorizer
                from models.transaction import Transaction
                ai_categorizer = AiCategorizer()
                if not ai_categorizer.enabled:
                    st.error("AI agent niet geconfigureerd.")
                else:
                    with st.spinner("AI analyseert..."):
                        # Pass database categories to AI context
                        user_categories = db_ops.get_categories(user_id)
                        ai_categorizer.set_categories(user_categories)
                        
                        tx_objs = []
                        for _, r in selected_rows.iterrows():
                            tx = Transaction(
                                id=r['id'],
                                datum=r['Datum'],
                                bedrag=Decimal(str(r['Bedrag'])),
                                naam_tegenpartij=r['Tegenpartij'],
                                omschrijving=r['Omschrijving'],
                                categorie=r['Categorie']
                            )
                            tx_objs.append(tx)
                        
                        optimized_txs = ai_categorizer.analyze_batch(tx_objs)
                        
                        if not any(t.ai_category for t in optimized_txs):
                            st.warning(" Geen AI details gevonden.")
                            return

                        # Update DB
                        # Logic: 
                        # 1. If AI suggests KNOWN category -> Update ID immediately
                        # 2. If AI suggests UNKNOWN category -> Update metadata (ai_category) but keep current category_id
                        
                        user_categories = db_ops.get_categories(user_id)
                        cat_name_to_id = {c['name']: c['id'] for c in user_categories}
                        new_cats_found = set()
                        
                        for tx in optimized_txs:
                            c_id = None
                            # Check if AI suggestion exists in DB
                            if tx.ai_category and tx.ai_category in cat_name_to_id:
                                # Safe to update category
                                if tx.categorie == tx.ai_category: # Only if our logic accepted it (confidence > 0.5)
                                    c_id = cat_name_to_id.get(tx.categorie)
                            elif tx.ai_category and tx.ai_confidence > 0.5:
                                # New valid suggestion?
                                new_cats_found.add(tx.ai_category)

                            updates = {
                                "naam_tegenpartij": tx.naam_tegenpartij,
                                "ai_name": tx.ai_name,
                                "ai_reasoning": tx.ai_reasoning,
                                "ai_confidence": tx.ai_confidence,
                                "ai_category": tx.ai_category
                            }
                            if c_id:
                                updates["categorie_id"] = c_id
                                
                            db_ops.update_transaction(tx.id, updates, user_id)
                        
                        if new_cats_found:
                            st.session_state['new_ai_cats'] = list(new_cats_found)
                        
                        st.success(f" {len(optimized_txs)} geoptimaliseerd!")
                        if new_cats_found:
                             st.info(f" AI suggereert nieuwe categorieën: {', '.join(new_cats_found)}")
                        
                        st.session_state.pending_trans_reload = True
                        st.rerun()

    with col_sel_all:
        if st.button("Alles", key="btn_sel_all_top", use_container_width=True, help="Selecteer alle getoonde transacties"):
            st.session_state.pending_trans_df.loc[filtered_df.index, 'Select'] = True
            st.rerun()

    with col_desel_all:
        if st.button("Niets", key="btn_desel_all_top", use_container_width=True, help="Deselecteer alle getoonde transacties"):
            st.session_state.pending_trans_df.loc[filtered_df.index, 'Select'] = False
            st.rerun()



    # Calculate height to avoid scrolling (approx 35px per row + 38px header + buffer)
    # Max height to prevent page becoming too huge, e.g., 2000px
    row_height = 35
    header_height = 40
    calculated_height = (len(filtered_df) * row_height) + header_height + 10
    
    # Display Data Editor
    edited_df = st.data_editor(
        filtered_df,
        column_config={
            "Select": st.column_config.CheckboxColumn("", width="small", default=False),
            "Datum": st.column_config.DateColumn("Datum", format="DD/MM/YYYY", step=1),
            "Tegenpartij": st.column_config.TextColumn("Tegenpartij", required=True),
            "Bedrag": st.column_config.NumberColumn("Bedrag", format=" %.2f"),
            "Categorie": st.column_config.SelectboxColumn("Categorie", options=db_category_names, required=True),
            "Lopende": st.column_config.CheckboxColumn("", help="Lopende rekening", default=False, width="small"),
            "Omschrijving": None, # Hide description
            "AI Naam": st.column_config.TextColumn(" AI Naam", disabled=True),

            "AI Motivatie": st.column_config.TextColumn(" Motivatie", disabled=True),
            "Vertrouwen": st.column_config.ProgressColumn(" Vertrouwen", format="%.0f%%", min_value=0, max_value=1),
            "id": None # Hide ID column
        },

        hide_index=True,
        use_container_width=True,
        height=calculated_height, 
        key="editor_pending",
        on_change=handle_pending_change,
        args=(user_id, db_ops)
    )

    # Note: We NO LONGER do st.session_state.pending_trans_df = edited_df.copy() here.
    # Doing so resets the data source for st.data_editor and clears its visual sort state.
    # The callback handles real-time persistence.




    st.divider()

def handle_history_change(user_id: str, db_ops: DatabaseOperations):
    """Callback for st.data_editor on_change in show_confirmed_history."""
    state = st.session_state.get("editor_history")
    if not state or not state.get("edited_rows"):
        return
        
    df = st.session_state.history_df_state
    edits = state["edited_rows"]
    
    # Rebuild filtered_hist to map positions back to actual indices
    df_filtered = df.copy()
    search_h = st.session_state.get("history_search")
    if search_h:
        q = search_h.lower()
        mask = (
            df_filtered['Tegenpartij'].str.lower().str.contains(q, na=False) |
            df_filtered['Categorie'].str.lower().str.contains(q, na=False) |
            df_filtered['Omschrijving'].str.lower().str.contains(q, na=False) |
            df_filtered['AI Naam'].str.lower().str.contains(q, na=False) |
            df_filtered['AI Motivatie'].str.lower().str.contains(q, na=False)
        )
        df_filtered = df_filtered[mask]

    # We need categories for ID lookup - Cache aware
    if 'user_categories_cache' not in st.session_state:
         st.session_state.user_categories_cache = db_ops.get_categories(user_id)
    user_categories = st.session_state.user_categories_cache
    
    cat_name_to_id = {c['name']: c['id'] for c in user_categories}
    
    for pos_str, changes in edits.items():
        pos = int(pos_str)
        if pos >= len(df_filtered): continue
        
        idx = df_filtered.index[pos]
        row_id = df.at[idx, 'id']
        current_row = df.loc[idx]
        
        # Batch category logic
        if "Categorie" in changes:
            new_cat_name = changes["Categorie"]
            is_selected = edits.get(pos_str, {}).get("Select", current_row["Select"])
            
            if is_selected:
                c_id = cat_name_to_id.get(new_cat_name)
                # Iterate df_filtered to find other selected rows for visual update
                for other_pos, (other_idx, row) in enumerate(df_filtered.iterrows()):
                    other_pos_str = str(other_pos)
                    other_sel = edits.get(other_pos_str, {}).get("Select", row["Select"])
                    
                    if other_sel and other_idx != idx:
                        if c_id:
                            db_ops.update_transaction(row['id'], {"categorie_id": c_id}, user_id)
                        if other_pos_str not in edits: edits[other_pos_str] = {}
                        edits[other_pos_str]["Categorie"] = new_cat_name

        # Batch Lopende (Current Account) Logic
        if "Lopende" in changes:
            new_val = bool(changes["Lopende"])
            is_selected = edits.get(pos_str, {}).get("Select", current_row["Select"])
            
            if is_selected:
                # Iterate df_filtered to find other selected rows for visual update
                for other_pos, (other_idx, row) in enumerate(df_filtered.iterrows()):
                    other_pos_str = str(other_pos)
                    other_sel = edits.get(other_pos_str, {}).get("Select", row["Select"])
                    
                    if other_sel and other_idx != idx:
                         db_ops.update_transaction(row['id'], {"is_lopende_rekening": new_val}, user_id)
                         # Update session state DF immediately
                         df.at[other_idx, 'Lopende'] = new_val
                         
                         if other_pos_str not in edits: edits[other_pos_str] = {}
                         edits[other_pos_str]["Lopende"] = new_val

        # Prepare main row update
        cat_val = changes.get("Categorie", current_row["Categorie"])
        c_id = cat_name_to_id.get(cat_val)

        # Update session state DF immediately
        if "Categorie" in changes: df.at[idx, "Categorie"] = cat_val
        if "Lopende" in changes: df.at[idx, "Lopende"] = bool(changes["Lopende"])
        if "Tegenpartij" in changes: df.at[idx, "Tegenpartij"] = str(changes["Tegenpartij"])
        if "Omschrijving" in changes: df.at[idx, "Omschrijving"] = str(changes["Omschrijving"])
        if "Bedrag" in changes: df.at[idx, "Bedrag"] = float(changes["Bedrag"])
        
        updates = {
            "datum": changes.get("Datum", current_row["Datum"]).isoformat() if hasattr(changes.get("Datum", current_row["Datum"]), "isoformat") else str(changes.get("Datum", current_row["Datum"])),
            "bedrag": float(changes.get("Bedrag", current_row["Bedrag"])),
            "naam_tegenpartij": str(changes.get("Tegenpartij", current_row["Tegenpartij"])),
            "omschrijving": str(changes.get("Omschrijving", current_row["Omschrijving"])),
            "categorie_id": c_id,
            "is_lopende_rekening": bool(changes.get("Lopende", current_row["Lopende"]))
        }
        db_ops.update_transaction(row_id, updates, user_id)

@st.fragment
def show_confirmed_history(user_id: str, db_ops: DatabaseOperations):
    """Show confirmed transactions with filters."""
    
    st.subheader("Historiek van Bevestigde Transacties")
    
    # 1. Filter UI
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Use Cache for History too
        if 'user_categories_cache' not in st.session_state:
             st.session_state.user_categories_cache = db_ops.get_categories(user_id)
        user_categories = st.session_state.user_categories_cache

        db_valid_cats = sorted([c['name'] for c in user_categories])
        if "Overig" not in db_valid_cats: db_valid_cats.append("Overig")
        all_cats = ["Alle"] + db_valid_cats
        selected_cat = st.selectbox("Categorie", all_cats)
    
    with col2:
        start_date = st.date_input("Vanaf", value=date.today() - timedelta(days=365))
    
    with col3:
        end_date = st.date_input("Tot", value=date.today())
    
    # 2. CACHING LOGIC
    cat_filter = None if selected_cat == "Alle" else selected_cat
    current_filters = {"cat": cat_filter, "start": start_date.isoformat(), "end": end_date.isoformat()}
    
    if "hist_reload_needed" not in st.session_state:
        st.session_state.hist_reload_needed = True
    
    filters_changed = st.session_state.get("last_hist_filters") != current_filters
    
    if st.session_state.hist_reload_needed or filters_changed or "history_df_state" not in st.session_state:
        transactions = db_ops.get_transactions(user_id, is_confirmed=True, category=cat_filter, start_date=start_date, end_date=end_date)
        df_data = []
        for t in transactions:
            display_name = t.get('naam_tegenpartij')
            if not display_name or display_name.strip() in ["", "-", "--", "---"]: display_name = "Onbekend"
            df_data.append({
                "Select": False,
                "Datum": datetime.strptime(t['datum'], '%Y-%m-%d').date() if isinstance(t['datum'], str) else t['datum'],
                "Tegenpartij": display_name,
                "Bedrag": float(t['bedrag']),
                "Categorie": t.get('categorie', 'Overig'),
                "Lopende": t.get('is_lopende_rekening', False),
                "Omschrijving": t.get('omschrijving', '') or "",
                "AI Naam": t.get('ai_name', ''),
                "AI Motivatie": t.get('ai_reasoning', ''),
                "Vertrouwen": float(t.get('ai_confidence') or 0.0),
                "id": t['id']
            })


        st.session_state.history_df_state = pd.DataFrame(df_data)
        st.session_state.last_hist_filters = current_filters
        st.session_state.hist_reload_needed = False
        if 'editor_history' in st.session_state: del st.session_state.editor_history

    df = st.session_state.history_df_state
    if df.empty:
        st.info("Geen bevestigde transacties gevonden voor deze filters")
        return

    cat_name_to_id = {c['name']: c['id'] for c in user_categories}
    db_category_names = sorted([c['name'] for c in user_categories])
    if "Overig" not in db_category_names: db_category_names.append("Overig")

    #  Broad Search for History
    st.write(f"**{len(df)}** bevestigde transacties")
    search_hist = st.text_input(" Broad Search", placeholder="Zoek op naam, omschrijving, AI details...", key="history_search", label_visibility="collapsed")
    
    # Apply text filter to history DF
    filtered_hist = df.copy()
    if search_hist:
        q = search_hist.lower()
        mask = (
            filtered_hist['Tegenpartij'].str.lower().str.contains(q, na=False) |
            filtered_hist['Categorie'].str.lower().str.contains(q, na=False) |
            filtered_hist['Omschrijving'].str.lower().str.contains(q, na=False) |
            filtered_hist['AI Naam'].str.lower().str.contains(q, na=False) |
            filtered_hist['AI Motivatie'].str.lower().str.contains(q, na=False)
        )
        filtered_hist = filtered_hist[mask]
    
    # Combined Action Row for History
    col_unconfirm, col_delete, col_ai, col_sel_all, col_desel_all = st.columns([1.5, 1.5, 2, 1.5, 1.5])
    
    with col_unconfirm:
        if st.button("Onbevestigd", key="btn_unconfirm_hist_top", use_container_width=True, help="Markeer geselecteerde transacties als onbevestigd"):
            selected_ids = filtered_hist[filtered_hist['Select']]['id'].tolist()
            if selected_ids:
                for tid in selected_ids: db_ops.update_transaction(tid, {"is_confirmed": False}, user_id)
                st.success("Transacties teruggezet.")
                st.session_state.hist_reload_needed = True
                st.session_state.pending_trans_reload = True
                st.rerun()

    with col_delete:
        if st.button("Verwijder", key="btn_delete_hist_top", use_container_width=True, help="Verwijder geselecteerde transacties definitief"):
            selected_ids = filtered_hist[filtered_hist['Select']]['id'].tolist()
            if selected_ids:
                for tid in selected_ids: db_ops.delete_transaction(tid, user_id)
                st.success("Transacties verwijderd.")
                st.session_state.hist_reload_needed = True
                st.rerun()

    with col_ai:
        if st.button("AI Her-cat", key="btn_ai_opt_hist_top", help="Laat de AI agent opnieuw kijken naar de geselecteerde transacties", use_container_width=True):
            selected_rows = filtered_hist[filtered_hist["Select"] == True]
            if selected_rows.empty:
                st.warning("Selecteer eerst transacties.")
            else:
                from services.ai_categorizer import AiCategorizer
                from models.transaction import Transaction
                ai_categorizer = AiCategorizer()
                
                with st.spinner("AI wordt uitgevoerd..."):
                    user_categories = db_ops.get_categories(user_id)
                    ai_categorizer.set_categories(user_categories)
                    
                    tx_objs = [Transaction(id=r['id'], datum=r['Datum'], bedrag=Decimal(str(r['Bedrag'])), 
                                          naam_tegenpartij=r['Tegenpartij'], omschrijving=r.get('Omschrijving', ''),
                                          categorie=r['Categorie']) 
                              for _, r in selected_rows.iterrows()]
                    
                    cat_name_to_id = {c['name']: c['id'] for c in user_categories}
                    optimized_txs = ai_categorizer.analyze_batch(tx_objs)

                    if not any(t.ai_reasoning for t in optimized_txs):
                        st.warning(" Geen AI details gevonden. Controleer of de API key correct is ingesteld in het .env bestand.")
                        return
                    
                    for tx in optimized_txs:
                        # Determine category ID - use AI suggestion if confident, else keep existing
                        new_cat_id = None
                        if tx.ai_category and tx.ai_confidence > 0.5:
                             # Try to match AI category to DB
                             matched_db_cat = cat_name_to_id.get(tx.ai_category)
                             if matched_db_cat:
                                 new_cat_id = matched_db_cat
                             else:
                                 # AI suggests a category we don't have yet. 
                                 # For now, we only update metadata, or we could fallback to 'Overig' if we wanted.
                                 pass
                        
                        updates = {
                            "naam_tegenpartij": tx.naam_tegenpartij, 
                            "ai_name": tx.ai_name, 
                            "ai_reasoning": tx.ai_reasoning, 
                            "ai_confidence": tx.ai_confidence,
                            "ai_category": tx.ai_category
                        }
                        
                        if new_cat_id:
                            updates["categorie_id"] = new_cat_id
                            
                        db_ops.update_transaction(tx.id, updates, user_id)
                    
                    st.success(" Historiek geoptimaliseerd!")
                    st.session_state.hist_reload_needed = True
                    st.rerun()

    with col_sel_all:
        if st.button("Alles", key="btn_sel_all_hist_top", use_container_width=True):
            st.session_state.history_df_state.loc[filtered_hist.index, 'Select'] = True
            st.rerun()

    with col_desel_all:
        if st.button("Niets", key="btn_desel_all_hist_top", use_container_width=True):
            st.session_state.history_df_state.loc[filtered_hist.index, 'Select'] = False
            st.rerun()


    row_height = 35
    header_height = 40
    calculated_height = (len(filtered_hist) * row_height) + header_height + 10
    
    edited_df = st.data_editor(
        filtered_hist,
        column_config={
            "Select": st.column_config.CheckboxColumn("", width="small", default=False),
            "Datum": st.column_config.DateColumn("Datum", format="DD/MM/YYYY"),
            "Tegenpartij": st.column_config.TextColumn("Tegenpartij"),
            "Bedrag": st.column_config.NumberColumn("Bedrag", format=" %.2f"),
            "Categorie": st.column_config.SelectboxColumn("Categorie", options=db_category_names, required=True),
            "Lopende": st.column_config.CheckboxColumn("", help="Lopende rekening", default=False, width="small"),
            "Omschrijving": None, # Hide description
            "AI Naam": st.column_config.TextColumn(" AI Naam", disabled=True),

            "AI Motivatie": st.column_config.TextColumn(" Motivatie", disabled=True),
            "Vertrouwen": st.column_config.ProgressColumn(" Vertrouwen", format="%.0f%%", min_value=0, max_value=1),
            "id": None
        },

        hide_index=True,
        use_container_width=True,
        height=calculated_height,
        key="editor_history",
        on_change=handle_history_change,
        args=(user_id, db_ops)
    )






def show_rules_management(user_id: str, db_ops: DatabaseOperations):
    """Show category rules management interface."""
    
    st.subheader("Categorisatieregels Beheren")
    
    user_categories = db_ops.get_categories(user_id)
    
    if not user_categories:
        st.info("Je hebt nog geen aangepaste categorieën. Deze worden automatisch aangemaakt wanneer je transacties corrigeert.")
        return
    
    # Display existing categories and rules
    for category in user_categories:
        with st.expander(f" {category['name']}", expanded=False):
            st.markdown(f"**Kleur:** {category.get('color', '#9ca3af')}")
            
            rules = category.get('rules', [])
            # Extract existing keywords from rules
            current_keywords = set()
            other_rules = []
            
            for rule in rules:
                field = rule.get('field', '')
                contains = rule.get('contains', [])
                
                # Collect keywords from text-based rules
                if field in ['naam_tegenpartij', 'omschrijving'] and contains:
                    current_keywords.update(contains)
                else:
                    # Keep non-text rules (like amount conditions) preserved
                    other_rules.append(rule)
            
            # Form for editing
            with st.form(f"rules_form_{category['id']}"):
                st.write("**Trefwoorden** (komma-gescheiden)")
                st.caption("Transacties met deze woorden in naam of omschrijving worden automatisch aan deze categorie gekoppeld.")
                
                keywords_str = st.text_area(
                    "Trefwoorden",
                    value=", ".join(sorted(current_keywords)),
                    key=f"keywords_{category['id']}",
                    label_visibility="collapsed"
                )
                
                col_save, col_del = st.columns([1, 5])
                with col_save:
                    if st.form_submit_button(" Opslaan"):
                        # Process new keywords
                        new_keywords = [k.strip() for k in keywords_str.split(',') if k.strip()]
                        
                        # Reconstruct rules
                        new_rules = other_rules.copy()
                        
                        if new_keywords:
                            # Create rules for both fields to ensure broad matching
                            new_rules.append({
                                "field": "naam_tegenpartij",
                                "contains": new_keywords
                            })
                            new_rules.append({
                                "field": "omschrijving",
                                "contains": new_keywords
                            })
                        
                        if db_ops.update_category_rules(category['id'], new_rules, user_id):
                            st.success("Regels bijgewerkt!")
                            st.rerun()
                        else:
                            st.error("Kon regels niet opslaan")
                
                with col_del:
                    pass # Spacer
            
            # Delete category button (outside form)
            if st.button(f" Verwijder Categorie", key=f"del_{category['id']}"):
                 st.warning("Verwijderen van categorieën is momenteel niet beschikbaar")
    
    st.divider()
    
    # Add new category
    st.subheader("Nieuwe Categorie Toevoegen")
    
    with st.form("new_category_form"):
        new_cat_name = st.text_input("Categorienaam")
        new_cat_color = st.color_picker("Kleur", "#9ca3af")
        submit = st.form_submit_button("Toevoegen")
        
        if submit:
            if new_cat_name:
                from models.category import Category
                new_category = Category(
                    name=new_cat_name,
                    color=new_cat_color,
                    rules=[]
                )
                success = db_ops.create_category(new_category, user_id)
                if success:
                    st.success(f" Categorie '{new_cat_name}' toegevoegd!")
                    st.rerun()
                else:
                    st.error(" Fout bij toevoegen van categorie")
            else:
                st.error("Vul een categorienaam in")
