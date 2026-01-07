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
    
    st.title("🏷️ Categorisatie Beheren")
    
    user = get_current_user()
    if not user:
        st.error("Je moet ingelogd zijn om categorieën te beheren")
        return
    
    db_ops = DatabaseOperations()
    
    # Tabs for different views
    tab1, tab2, tab3 = st.tabs(["📬 Te Bevestigen", "📜 Historiek", "⚙️ Regels Beheren"])
    
    with tab1:
        show_pending_review(user.id, db_ops)
    
    with tab2:
        show_confirmed_history(user.id, db_ops)
    
    with tab3:
        show_rules_management(user.id, db_ops)

import pandas as pd
from datetime import datetime, date, timedelta

@st.fragment
def show_pending_review(user_id: str, db_ops: DatabaseOperations):
    """Show pending (unconfirmed) transactions review interface."""
    
    st.subheader("Onbevestigde Transacties")
    
    # Fetch unconfirmed transactions
    transactions = db_ops.get_transactions(user_id, is_confirmed=False)
    
    if not transactions:
        st.success("✨ Alle transacties zijn bevestigd!")
        return
    
    # Get category list and mapping
    user_categories = db_ops.get_categories(user_id)
    cat_name_to_id = {c['name']: c['id'] for c in user_categories}
    cat_engine = CategorizationEngine(user_categories)
    
    # STRICTLY use DB categories
    db_category_names = sorted([c['name'] for c in user_categories])
    if "Overig" not in db_category_names:
        db_category_names.append("Overig")
    
    # Quick Add Category (since table dropdown can't easily handle "create new" with custom name input)
    with st.expander("➕ Nieuwe Categorie Aanmaken", expanded=False):
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
                        st.rerun()
                    else:
                        st.error("Kon categorie niet aanmaken")
                else:
                    st.warning("Vul een naam in")

    st.write(f"**{len(transactions)}** transacties wachten op bevestiging")

    # Convert to DataFrame for editing
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
            "id": t['id'] # Hidden column
        })
    
    df = pd.DataFrame(df_data)

    # Calculate height to avoid scrolling (approx 35px per row + 38px header + buffer)
    # Max height to prevent page becoming too huge, e.g., 2000px
    row_height = 35
    header_height = 40
    calculated_height = (len(df) * row_height) + header_height + 10
    
    # Display Data Editor
    edited_df = st.data_editor(
        df,
        column_config={
            "Select": st.column_config.CheckboxColumn(
                "✅",
                width="small",
                default=False,
            ),
            "Datum": st.column_config.DateColumn(
                "Datum",
                format="DD/MM/YYYY",
                step=1,
            ),
            "Tegenpartij": st.column_config.TextColumn(
                "Tegenpartij",
                required=True,
            ),
            "Bedrag": st.column_config.NumberColumn(
                "Bedrag",
                format="€ %.2f",
            ),
            "Categorie": st.column_config.SelectboxColumn(
                "Categorie",
                options=db_category_names,
                required=True,
            ),
            "Lopende": st.column_config.CheckboxColumn(
                "⏳",
                help="Markeer als lopende rekening (vooruitbetaald)",
                default=False,
                width="small"
            ),
            "Omschrijving": st.column_config.TextColumn(
                "Omschrijving",
            ),
            "id": None # Hide ID column
        },
        hide_index=True,
        use_container_width=True,
        height=calculated_height, 
        key="editor_pending"
    )

    # Bulk Actions
    col_confirm, col_delete, col_spacer = st.columns([1, 1, 3])
    
    with col_confirm:
        if st.button("✅ Bevestig Selectie & Opslaan", type="primary", use_container_width=True):
            # Create a lookup for original transactions
            trans_map = {t['id']: t for t in transactions}
            
            success_count = 0
            saved_count = 0
            
            for index, row in edited_df.iterrows():
                trans_id = row['id']
                original_trans = trans_map.get(trans_id)
                
                if not original_trans:
                    continue
                    
                # Determine if confirmed
                is_selected = row['Select']
                
                # Check for changes
                new_category_name = row['Categorie']
                cat_id = cat_name_to_id.get(new_category_name)
                
                if not cat_id:
                    st.error(f"Categorie '{new_category_name}' niet gevonden.")
                    continue
                
                # Prepare value for DB
                current_values = {
                    "datum": row['Datum'].isoformat(),
                    "bedrag": float(row['Bedrag']),
                    "naam_tegenpartij": row['Tegenpartij'],
                    "omschrijving": row['Omschrijving'],
                    "categorie_id": cat_id,
                    "is_confirmed": is_selected,
                    "is_lopende_rekening": row['Lopende']
                }
                
                # Compare with original
                orig_cat = original_trans.get('categorie', 'Overig')
                if orig_cat not in db_category_names: orig_cat = "Overig"
                
                has_changes = (
                    original_trans['datum'] != current_values['datum'] or
                    float(original_trans['bedrag']) != current_values['bedrag'] or
                    (original_trans['naam_tegenpartij'] or "") != current_values['naam_tegenpartij'] or
                    (original_trans['omschrijving'] or "") != current_values['omschrijving'] or
                    orig_cat != new_category_name or
                    original_trans.get('is_lopende_rekening', False) != current_values['is_lopende_rekening'] or
                    is_selected
                )
                
                if has_changes:
                    # Perform Update
                    updates = current_values
                    
                    if db_ops.update_transaction(trans_id, updates, user_id):
                        if is_selected:
                            success_count += 1
                            
                            # Learning Logic
                            original_auto_cat = original_trans.get('categorie')
                            if new_category_name != original_auto_cat:
                                 trans_obj = Transaction(
                                    datum=row['Datum'],
                                    bedrag=Decimal(str(row['Bedrag'])),
                                    naam_tegenpartij=row['Tegenpartij'],
                                    omschrijving=row['Omschrijving']
                                )
                                 learned_rule = cat_engine.learn_from_correction(trans_obj, new_category_name)
                                 
                                 if learned_rule and learned_rule.get('rule'):
                                    existing_cat = db_ops.get_category_by_name(new_category_name, user_id)
                                    if existing_cat:
                                        current_rules = existing_cat.get('rules', [])
                                        if not any(r == learned_rule['rule'] for r in current_rules):
                                            current_rules.append(learned_rule['rule'])
                                            db_ops.update_category_rules(existing_cat['id'], current_rules, user_id)
                        else:
                            saved_count += 1
            
            if success_count > 0 or saved_count > 0:
                msg = []
                if success_count > 0: msg.append(f"{success_count} bevestigd")
                if saved_count > 0: msg.append(f"{saved_count} opgeslagen")
                st.success(f"Actie voltooid: {', '.join(msg)}!")
                st.rerun()
    
    with col_delete:
        if st.button("🗑️ Selectie Verwijderen", type="secondary", use_container_width=True):
            # Get selected transactions
            selected_rows = edited_df[edited_df["Select"] == True]
            
            if selected_rows.empty:
                st.warning("Selecteer ten minste één transactie om te verwijderen.")
            else:
                deleted_count = 0
                for index, row in selected_rows.iterrows():
                    trans_id = row['id']
                    if db_ops.delete_transaction(trans_id, user_id):
                        deleted_count += 1
                
                if deleted_count > 0:
                    st.success(f"{deleted_count} transacties verwijderd!")
                    st.rerun()

    # Handle inline edits (optional: save changes even without confirming?)
    # For now, we only save when "Confirm" is clicked. 
    # User might expect "editing" to just save locally until confirmed.
    # If the user edits a field but DOES NOT select the checkbox, the edit is effectively "lost" upon rerun if we don't handle it.
    # However, st.data_editor state persists across reruns.
    # But if real-time persistence is needed for UNCONFIRMED edits, we'd need to compare edited_df with 'transactions' and trigger updates.
    # Given the request focused on "checkbox to select", bulk confirmation is the standard pattern.
    
    st.divider()

def show_confirmed_history(user_id: str, db_ops: DatabaseOperations):
    """Show confirmed transactions with filters."""
    
    st.subheader("Historiek van Bevestigde Transacties")
    
    # Filter options
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Category filter
        user_categories = db_ops.get_categories(user_id)
        cat_engine = CategorizationEngine(user_categories)
        all_cats = ["Alle"] + cat_engine.get_category_names()
        selected_cat = st.selectbox("Categorie", all_cats)
    
    with col2:
        start_date = st.date_input("Vanaf", value=date.today() - timedelta(days=365))
    
    with col3:
        end_date = st.date_input("Tot", value=date.today())
    
    # Fetch confirmed transactions
    cat_filter = None if selected_cat == "Alle" else selected_cat
    transactions = db_ops.get_transactions(
        user_id, 
        is_confirmed=True, 
        category=cat_filter,
        start_date=start_date,
        end_date=end_date
    )
    
    if not transactions:
        st.info("Geen bevestigde transacties gevonden voor deze filters")
        return
    
    st.write(f"**{len(transactions)}** bevestigde transacties")
    
    # Show as a simplified list or dataframe
    df_data = []
    for t in transactions:
        display_name = t.get('naam_tegenpartij')
        if not display_name or display_name.strip() in ["", "-", "--", "---"]:
            display_name = "Onbekend"
            
        df_data.append({
            'Datum': t['datum'],
            'Tegenpartij': display_name,
            'Bedrag': f"€{t['bedrag']:,.2f}",
            'Categorie': t.get('categorie', 'Overig'),
            'Omschrijving': t.get('omschrijving', '')
        })
    
    st.dataframe(pd.DataFrame(df_data), use_container_width=True, hide_index=True)

def show_rules_management(user_id: str, db_ops: DatabaseOperations):
    """Show category rules management interface."""
    
    st.subheader("Categorisatieregels Beheren")
    
    user_categories = db_ops.get_categories(user_id)
    
    if not user_categories:
        st.info("Je hebt nog geen aangepaste categorieën. Deze worden automatisch aangemaakt wanneer je transacties corrigeert.")
        return
    
    # Display existing categories and rules
    for category in user_categories:
        with st.expander(f"📁 {category['name']}", expanded=False):
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
                    if st.form_submit_button("💾 Opslaan"):
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
            if st.button(f"🗑️ Verwijder Categorie", key=f"del_{category['id']}"):
                 st.warning("Verwijderen van categorieën is momenteel niet beschikbaar")
    
    st.divider()
    
    # Add new category
    st.subheader("➕ Nieuwe Categorie Toevoegen")
    
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
                    st.success(f"✅ Categorie '{new_cat_name}' toegevoegd!")
                    st.rerun()
                else:
                    st.error("❌ Fout bij toevoegen van categorie")
            else:
                st.error("Vul een categorienaam in")
