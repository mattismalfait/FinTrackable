"""
CSV upload interface with intelligent category suggestion.
"""

import streamlit as st
from services.csv_parser import CSVParser
from services.category_suggester import CategorySuggester
from services.categorization import CategorizationEngine
from database.operations import DatabaseOperations
from views.auth import get_current_user
from models.category import Category
import pandas as pd

from utils.ui.template_loader import load_template

def show_upload_page():
    """Display CSV upload and import interface."""
    
    # Initialize session state if not present
    if 'upload_step' not in st.session_state:
        st.session_state['upload_step'] = 'upload'
    
    # Custom Stepper HTML using templates
    steps = ["Uploaden", "Controleren", "Importeren"]
    current_step_idx = 0
    if st.session_state['upload_step'] == 'review_categories':
        current_step_idx = 1
    elif st.session_state['upload_step'] == 'import':
        current_step_idx = 2
        
    container_template = load_template("components/stepper.html")
    item_template = load_template("components/stepper_item.html")
    
    steps_content = ""
    for i, step in enumerate(steps):
        is_active = i <= current_step_idx
        steps_content += item_template.format(
            index=i+1,
            label=step,
            bg="#eff6ff" if is_active else "white",
            border="2px solid #3b82f6" if is_active else "2px solid #e2e8f0",
            color="#3b82f6" if is_active else "#94a3b8"
        )
    
    st.markdown(container_template.format(steps_content=steps_content), unsafe_allow_html=True)
    
    with st.expander("💡 Hoe werkt de categorisatie?", expanded=False):
        st.info("""
        **FinTrackable gebruikt een slimme combinatie van regels:**
        
        1. **Automatische Herkenning**: Het systeem zoekt naar trefwoorden in de *Naam tegenpartij* en *Omschrijving*.
        2. **Bedrag Analyse**: Bijv. positieve bedragen worden vaak als 'Inkomen' herkend.
        3. **Leersysteem**: Zodra je categorieën goedkeurt of aanpast, onthoudt het systeem dit voor toekomstige imports.
        
        *Bijv. 'Saxo' wordt herkend als 'Investeren', en 'Delhaize' als 'Eten & Drinken'.*
        """)
    
    #Initialize session state for upload workflow
    if 'upload_step' not in st.session_state:
        st.session_state['upload_step'] = 'upload'
    if 'parsed_transactions' not in st.session_state:
        st.session_state['parsed_transactions'] = None
    if 'suggested_categories' not in st.session_state:
        st.session_state['suggested_categories'] = None
    if 'approved_categories' not in st.session_state:
        st.session_state['approved_categories'] = {}
    
    # Show appropriate step
    if st.session_state['upload_step'] == 'upload':
        show_file_upload()
    elif st.session_state['upload_step'] == 'review_categories':
        show_category_review()
    elif st.session_state['upload_step'] == 'import':
        show_import_confirmation()

def show_file_upload():
    """Step 1: File upload and parsing."""
    
    uploaded_file = st.file_uploader(
        "Kies een CSV-bestand",
        type=['csv'],
        key="csv_uploader_key",
        help="Upload een KBC CSV-bestand met kolommen: Datum, Bedrag, Naam tegenpartij, Omschrijving"
    )
    
    if uploaded_file is not None:
        user = get_current_user()
        if not user:
            st.error("Je moet ingelogd zijn om bestanden te uploaden")
            return
        
        parser = CSVParser()
        
        with st.spinner("CSV-bestand wordt verwerkt..."):
            transactions, df, errors = parser.process_csv(uploaded_file)
            
            if errors:
                with st.expander("⚠️ Waarschuwingen", expanded=len(transactions) == 0):
                    for error in errors:
                        st.warning(error)
            
            # Filter out duplicates immediately
            if transactions:
                db_ops = DatabaseOperations()
                existing_hashes = db_ops.get_existing_hashes(user.id)
                
                # Generate hashes for new transactions (if not already done)
                unique_transactions = []
                duplicate_count = 0
                import hashlib
                
                for t in transactions:
                    if not t.hash:
                        t.generate_hash()
                    
                    # Calculate legacy hash for backward compatibility
                    # Old format: datum|bedrag|naam_tegenpartij|omschrijving
                    legacy_str = f"{t.datum}|{t.bedrag}|{t.naam_tegenpartij or ''}|{t.omschrijving or ''}"
                    legacy_hash = hashlib.md5(legacy_str.encode()).hexdigest()
                    
                    if t.hash in existing_hashes:
                        duplicate_count += 1
                        # st.write(f"Strict Duplicate: {t.hash}") # Debug
                    elif legacy_hash in existing_hashes:
                        duplicate_count += 1
                        # st.write(f"Legacy Duplicate: {legacy_hash} for {t.bedrag}") # Debug
                    else:
                        unique_transactions.append(t)
                        # Add both to set to prevent duplicates within the same upload file
                        existing_hashes.add(t.hash)
                        existing_hashes.add(legacy_hash)
                
                if duplicate_count > 0:
                    st.info(f"ℹ️ **{duplicate_count}** dubbele transacties zijn eruit gefilterd (al in systeem).")
                
                if not unique_transactions:
                    st.warning("⚠️ Alle geüploade transacties zitten al in het systeem.")
                    st.stop()
                    
                transactions = unique_transactions
                st.success(f"✅ {len(transactions)} nieuwe transacties klaar om te importeren")
            
            # Show preview
            with st.expander("📋 Voorbeeld transacties", expanded=True):
                preview_df = pd.DataFrame([{
                    'Datum': t.datum,
                    'Bedrag': f"€{t.bedrag:,.2f}",
                    'Tegenpartij': t.naam_tegenpartij or '-',
                    'Omschrijving': (t.omschrijving[:50] + '...') if t.omschrijving and len(t.omschrijving) > 50 else (t.omschrijving or '-')
                } for t in transactions[:10]])
                
                st.dataframe(preview_df, use_container_width=True, hide_index=True)
                
                if len(transactions) > 10:
                    st.info(f"... en {len(transactions) - 10} meer transacties")
            
            # Analyze and suggest categories
            if st.button("➡️ Doorgaan naar Categorie Suggesties", type="primary"):
                # db_ops initialized above
                user_categories = db_ops.get_categories(user.id)
                
                suggester = CategorySuggester(user_categories=user_categories)
                suggested_cats, processed_txns = suggester.analyze_and_suggest(transactions)
                
                st.session_state['parsed_transactions'] = processed_txns
                st.session_state['suggested_categories'] = suggested_cats
                st.session_state['upload_step'] = 'review_categories'
                st.rerun()

def show_category_review():
    """Step 2: Review and approve suggested categories."""
    
    st.subheader("🏷️ Voorgestelde Categorieën")
    st.markdown("Gebaseerd op je transacties, stel ik de volgende categorieën voor. Kies welke je wilt gebruiken:")
    
    suggested_cats = st.session_state['suggested_categories']
    
    if not suggested_cats:
        st.error("Geen categorieën gevonden")
        return
    
    # Initialize approved categories in session state if not exists
    if 'temp_approved_categories' not in st.session_state:
        st.session_state['temp_approved_categories'] = {}
    
    # Show category cards with checkboxes
    st.markdown("---")
    
    for cat_name, cat_data in suggested_cats.items():
        col1, col2 = st.columns([1, 4])
        
        with col1:
            # Color preview
            st.markdown(f"""
                <div style="background-color: {cat_data['color']}; 
                            width: 60px; 
                            height: 60px; 
                            border-radius: 10px;
                            margin: 10px;">
                </div>
            """, unsafe_allow_html=True)
        
        with col2:
            # Category checkbox and details
            is_approved = st.checkbox(
                f"**{cat_name}**",
                value=True,
                key=f"cat_{cat_name}"
            )
            
            # Show reasons why this was suggested
            if cat_data.get('reasons'):
                reasons_text = ", ".join(cat_data['reasons'])
                st.markdown(f"**Waarom?** *{reasons_text}*")
            
            st.caption(cat_data.get('description', ''))
            
            if cat_data['transaction_count'] > 0:
                st.caption(f"📊 {cat_data['transaction_count']} transacties | "
                          f"💶 Totaal: €{cat_data['avg_amount'] * cat_data['transaction_count']:,.2f}")
            
            # Show counterparties
            if cat_data.get('counterparties'):
                counterparties = sorted(cat_data['counterparties'])[:5]
                if counterparties:
                    st.caption(f"🏪 Gevonden bij: {', '.join(counterparties)}")
        
        st.markdown("---")
    
    # Show custom categories if any
    if st.session_state['temp_approved_categories']:
        st.markdown("### Eigen Categorieën:")
        for custom_name, custom_data in st.session_state['temp_approved_categories'].items():
            col1, col2 = st.columns([1, 4])
            
            with col1:
                st.markdown(f"""
                    <div style="background-color: {custom_data['color']}; 
                                width: 60px; 
                                height: 60px; 
                                border-radius: 10px;
                                margin: 10px;">
                    </div>
                """, unsafe_allow_html=True)
            
            with col2:
                col_a, col_b = st.columns([4, 1])
                with col_a:
                    st.write(f"**{custom_name}**")
                    st.caption(custom_data.get('description', 'Eigen categorie'))
                with col_b:
                    if st.button("🗑️", key=f"del_{custom_name}"):
                        del st.session_state['temp_approved_categories'][custom_name]
                        st.rerun()
            
            st.markdown("---")
    
    # Allow custom category addition
    with st.expander("➕ Voeg Eigen Categorie Toe"):
        with st.form("add_custom_category"):
            custom_name = st.text_input("Naam*")
            custom_color = st.color_picker("Kleur", "#10b981")
            custom_desc = st.text_input("Beschrijving (optioneel)")
            
            submitted = st.form_submit_button("Toevoegen")
            
            if submitted:
                if not custom_name:
                    st.error("Vul een naam in")
                elif custom_name in suggested_cats or custom_name in st.session_state['temp_approved_categories']:
                    st.error(f"Categorie '{custom_name}' bestaat al")
                else:
                    st.session_state['temp_approved_categories'][custom_name] = {
                        'name': custom_name,
                        'color': custom_color,
                        'description': custom_desc,
                        'counterparties': [],
                        'transaction_count': 0,
                        'avg_amount': 0,
                        'keywords': []
                    }
                    st.success(f"✅ Categorie '{custom_name}' toegevoegd")
                    st.rerun()
    
    # Navigation buttons
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("⬅️ Terug", use_container_width=True):
            st.session_state['upload_step'] = 'upload'
            st.session_state.pop('temp_approved_categories', None)
            st.rerun()
    
    with col2:
        if st.button("🔄 Reset", use_container_width=True):
            st.session_state.clear()
            st.rerun()
    
    with col3:
        if st.button("✅ Akkoord & Doorgaan", type="primary", use_container_width=True):
            # Collect all approved categories
            approved = {}
            
            # Add checked suggested categories
            for cat_name, cat_data in suggested_cats.items():
                if st.session_state.get(f"cat_{cat_name}", True):  # Default checked
                    approved[cat_name] = cat_data
            
            # Add custom categories
            approved.update(st.session_state.get('temp_approved_categories', {}))
            
            if not approved:
                st.error("Selecteer minstens één categorie")
            else:
                st.session_state['approved_categories'] = approved
                st.session_state['upload_step'] = 'import'
                st.session_state.pop('temp_approved_categories', None)
                st.rerun()


def show_import_confirmation():
    """Step 3: Import transactions with approved categories."""
    
    user = get_current_user()
    if not user:
        st.error("Je moet ingelogd zijn")
        return
    
    transactions = st.session_state['parsed_transactions']
    approved_cats = st.session_state['approved_categories']
    
    st.subheader("💾 Importeren")
    st.info(f"Klaar om {len(transactions)} transacties te importeren met {len(approved_cats)} categorieën")
    
    # Show summary
    with st.expander("📊 Samenvatting", expanded=True):
        st.write("**Goedgekeurde Categorieën:**")
        for cat_name in approved_cats.keys():
            st.write(f"• {cat_name}")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("⬅️ Terug naar Categorieën", use_container_width=True):
            st.session_state['upload_step'] = 'review_categories'
            st.rerun()
    
    with col2:
        if st.button("🚀 Importeren!", type="primary", use_container_width=True):
            perform_import(transactions, approved_cats, user.id)

def perform_import(transactions, approved_categories, user_id):
    """Perform the actual import with approved categories."""
    
    db_ops = DatabaseOperations()
    
    # Map for name -> id
    cat_name_to_id = {}
    
    with st.spinner("Categorieën worden aangemaakt..."):
        # Ensure "Overig" exists
        overig_cat = Category(name="Overig", color="#9ca3af", rules=[])
        overig_id = db_ops.create_category(overig_cat, user_id)
        cat_name_to_id["Overig"] = overig_id
        
        # Create approved categories in database
        for cat_name, cat_data in approved_categories.items():
            if cat_name == "Overig": continue
            
            # Translate keywords to rules
            rules = []
            if cat_data.get('keywords'):
                rules.append({
                    "field": "naam_tegenpartij",
                    "contains": cat_data['keywords']
                })
                # Support matching in description as well
                rules.append({
                    "field": "omschrijving",
                    "contains": cat_data['keywords']
                })
            
            if cat_name == "Inkomen":
                rules.append({"field": "bedrag", "condition": "positive"})
                
            try:
                new_cat = Category(
                    name=cat_name,
                    color=cat_data.get('color', '#9ca3af'),
                    rules=rules
                )
                cat_id = db_ops.create_category(new_cat, user_id)
                cat_name_to_id[cat_name] = cat_id
            except Exception as e:
                pass
    
    with st.spinner("Transacties worden geïmporteerd..."):
        # Link transactions to category IDs
        approved_names = set(approved_categories.keys())
        for t in transactions:
            # Determine correct name first (fallback to Overig)
            final_cat_name = t.categorie if t.categorie in approved_names else "Overig"
            
            # Assign ID from our map
            t.categorie_id = cat_name_to_id.get(final_cat_name, overig_id)
                
        result = db_ops.insert_transactions(transactions, user_id)
        
        # Show results
        st.success(f"✅ {result['success']} transacties succesvol geïmporteerd")
        
        if result['skipped'] > 0:
            st.info(f"ℹ️ {result['skipped']} dubbele transacties overgeslagen")
        
        if result['errors']:
            with st.expander(f"❌ {len(result['errors'])} fouten"):
                for error in result['errors']:
                    st.error(error)
        
        # Clear session state
        st.session_state.pop('upload_step', None)
        st.session_state.pop('parsed_transactions', None)
        st.session_state.pop('suggested_categories', None)
        st.session_state.pop('approved_categories', None)
        
        # Navigation
        if st.button("📊 Ga naar Dashboard"):
            st.session_state['page'] = 'dashboard'
            st.rerun()
