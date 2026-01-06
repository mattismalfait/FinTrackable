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
    
    # STRICTLY use DB categories + New option
    db_category_names = sorted([c['name'] for c in user_categories])
    # Ensure "Overig" is in the list if not present (though it should be)
    if "Overig" not in db_category_names:
        db_category_names.append("Overig")
        
    all_categories = db_category_names + ["➕ Nieuwe categorie..."]
    
    st.write(f"**{len(transactions)}** transacties wachten op bevestiging")
    
    # CSS to make the edit buttons look like plain, inline icons
    st.markdown("""
        <style>
        /* Target buttons within our specific container */
        .inline-edit-btn [data-testid="stButton"] button {
            border: none !important;
            background: transparent !important;
            padding: 0px !important;
            margin: 0px !important;
            min-height: unset !important;
            height: 20px !important;
            width: 20px !important;
            display: inline-flex !important;
            align-items: center !important;
            justify-content: center !important;
            box-shadow: none !important;
            color: #64748b !important; /* Muted gray by default */
            transition: color 0.2s ease !important;
        }
        .inline-edit-btn [data-testid="stButton"] button:hover {
            color: #1d4ed8 !important; /* Blue on hover */
            background: transparent !important;
        }
        .inline-edit-btn [data-testid="stButton"] button:active, 
        .inline-edit-btn [data-testid="stButton"] button:focus {
            background: transparent !important;
            box-shadow: none !important;
            outline: none !important;
            color: #1d4ed8 !important;
        }
        /* Further cleanup of Streamlit button artifacts */
        .inline-edit-btn div[data-testid="stButton"] {
            display: inline-block !important;
            vertical-align: middle !important;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Display transactions in editable format
    for idx, trans in enumerate(transactions):
        trans_id = trans['id']
        name_key = f"edit_name_{trans_id}"
        desc_key = f"edit_desc_{trans_id}"
        
        # Initialize session state keys if not present
        if name_key not in st.session_state: st.session_state[name_key] = False
        if desc_key not in st.session_state: st.session_state[desc_key] = False

        with st.container():
            # Main row layout: [Main Info (Name/Desc), Amount/Date, Category, Confirm Button]
            col1, col2, col3, col4 = st.columns([5, 1.5, 2, 0.7])
            
            with col1:
                # --- NAME FIELD ---
                display_name = trans.get('naam_tegenpartij')
                if not display_name or display_name.strip() in ["", "-", "--", "---"]:
                    display_name = "Onbekend"
                
                # Use a very tight layout to keep the pencil right next to the text
                name_cols = st.columns([20, 1], gap="small")
                with name_cols[0]:
                    if st.session_state[name_key]:
                        new_name = st.text_input("Naam", value=display_name, key=f"input_name_{trans_id}", label_visibility="collapsed")
                    else:
                        st.markdown(f"**{display_name}**")
                        new_name = display_name
                with name_cols[1]:
                    st.markdown('<div class="inline-edit-btn">', unsafe_allow_html=True)
                    if st.button("✎", key=f"btn_name_{trans_id}", help="Naam bewerken"):
                        st.session_state[name_key] = not st.session_state[name_key]
                        st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)

                # --- DESCRIPTION FIELD ---
                desc_cols = st.columns([20, 1], gap="small")
                with desc_cols[0]:
                    if st.session_state[desc_key]:
                        new_desc = st.text_input("Omschrijving", value=trans.get('omschrijving', ''), key=f"input_desc_{trans_id}", label_visibility="collapsed")
                    else:
                        st.caption(trans.get('omschrijving', '') or "Geen omschrijving")
                        new_desc = trans.get('omschrijving', '')
                with desc_cols[1]:
                    st.markdown('<div class="inline-edit-btn">', unsafe_allow_html=True)
                    if st.button("✎", key=f"btn_desc_{trans_id}", help="Omschrijving bewerken"):
                        st.session_state[desc_key] = not st.session_state[desc_key]
                        st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
            
            with col2:
                # Align amount and date
                st.markdown(f"### €{trans['bedrag']:,.2f}")
                st.caption(trans['datum'])
            
            with col3:
                # Category selector
                current_category = trans.get('categorie', 'Overig')
                cat_index = 0
                
                # If current category isn't in our DB list (ghost category), default to Overig or logic
                if current_category in db_category_names:
                    cat_index = db_category_names.index(current_category)
                else:
                    # Try fuzzy lowercase match
                    found = False
                    for i, name in enumerate(db_category_names):
                        if name.lower() == current_category.lower():
                            cat_index = i
                            found = True
                            break
                    if not found and "Overig" in db_category_names:
                        cat_index = db_category_names.index("Overig")

                new_category = st.selectbox(
                    "Categorie",
                    options=all_categories,
                    index=cat_index,
                    key=f"cat_{trans_id}",
                    label_visibility="collapsed"
                )
                
                custom_cat_name = None
                if new_category == "➕ Nieuwe categorie...":
                    custom_cat_name = st.text_input("Nieuwe naam", key=f"new_cat_inp_{trans_id}", placeholder="Typ naam...", label_visibility="collapsed")
            
            with col4:
                # Combined Save & Confirm button
                if st.button("✅", key=f"conf_{trans_id}", type="primary", use_container_width=True):
                    
                    final_category_id = None
                    final_category_name = new_category
                    
                    # Handle new category creation
                    if new_category == "➕ Nieuwe categorie...":
                        if custom_cat_name and custom_cat_name.strip():
                            # Create the new category
                            from models.category import Category
                            # Determine color (cycle or random)
                            import random
                            colors = ["#ef4444", "#f97316", "#f59e0b", "#84cc16", "#10b981", "#06b6d4", "#3b82f6", "#8b5cf6", "#ec4899"]
                            new_cat_obj = Category(name=custom_cat_name.strip(), color=random.choice(colors))
                            
                            created_id = db_ops.create_category(new_cat_obj, user_id)
                            if created_id:
                                final_category_id = created_id
                                final_category_name = custom_cat_name.strip()
                                st.toast(f"Categorie '{final_category_name}' aangemaakt!")
                            else:
                                st.error("Kon categorie niet aanmaken")
                                st.stop()
                        else:
                            st.warning("Vul een naam in voor de nieuwe categorie")
                            st.stop()
                    else:
                        final_category_id = cat_name_to_id.get(new_category)
                        final_category_name = new_category

                    updates = {
                        "is_confirmed": True,
                        "categorie_id": final_category_id,
                        "naam_tegenpartij": new_name,
                        "omschrijving": new_desc
                    }
                    
                    if db_ops.update_transaction(trans_id, updates, user_id):
                        # Learning logic
                        # If the final category is different from what was AUTO suggested (in 'categorie' field of trans)
                        # calculate rule.
                        current_auto_cat = trans.get('categorie')
                        if final_category_name != current_auto_cat:
                             trans_obj = Transaction(
                                datum=datetime.strptime(trans['datum'], '%Y-%m-%d').date() if isinstance(trans['datum'], str) else trans['datum'],
                                bedrag=Decimal(str(trans['bedrag'])),
                                naam_tegenpartij=new_name,
                                omschrijving=new_desc
                            )
                             # Note: learn_from_correction returns a rule dict
                             # It doesn't modify the new category, just suggests a rule for it
                             learned_rule = cat_engine.learn_from_correction(trans_obj, final_category_name)
                             
                             if learned_rule and learned_rule.get('rule'):
                                # Add this rule to the category (new or existing)
                                existing_cat = db_ops.get_category_by_name(final_category_name, user_id)
                                if existing_cat:
                                    current_rules = existing_cat.get('rules', [])
                                    # unique check
                                    if not any(r == learned_rule['rule'] for r in current_rules):
                                        current_rules.append(learned_rule['rule'])
                                        db_ops.update_category_rules(existing_cat['id'], current_rules, user_id)
                                        st.toast(f"💡 Regel geleerd voor '{final_category_name}'")
                        
                        # Cleanup session state
                        if name_key in st.session_state: del st.session_state[name_key]
                        if desc_key in st.session_state: del st.session_state[desc_key]
                        st.rerun()
            
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
