"""
CSV upload interface with intelligent category suggestion.
"""

import streamlit as st
from datetime import datetime
from services.universal_parser import UniversalParser
from services.ai_categorizer import AiCategorizer
from database.operations import DatabaseOperations
from models.transaction import Transaction
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
    if 'approved_categories' in st.session_state:
        st.session_state['temp_approved_categories'] = st.session_state.get('temp_approved_categories', {})

    
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
        "Kies een afschrift van je bank (CSV of Excel)",
        type=['csv', 'xlsx', 'xls'],
        key="csv_uploader_key",
        help="Upload een CSV of Excel bestand. FinTrackable herkent automatisch formaten van KBC, ING, Revolut, N26 en anderen."
    )
    
    if uploaded_file is not None:
        user = get_current_user()
        if not user:
            st.error("Je moet ingelogd zijn om bestanden te uploaden")
            return
        
        # Step: Upload & Parse
        parser = UniversalParser()
        
        with st.spinner("Bestand wordt geanalyseerd door AI..."):
            raw_transactions, df, messages = parser.process_file(uploaded_file)
            
            if messages:
                for msg in messages:
                    if "✅" in msg:
                        st.success(msg)
                    elif "⚠️" in msg:
                        st.info(msg)
                    elif "❌" in msg:
                        st.error(msg)
            
            if not raw_transactions:
                return

            # Filter out duplicates immediately
            db_ops = DatabaseOperations()
            existing_hashes = db_ops.get_existing_hashes(user.id)
            
            unique_transactions = []
            duplicate_count = 0
            import hashlib
            
            for t in raw_transactions:
                if not t.hash:
                    t.generate_hash()
                
                legacy_str = f"{t.datum}|{t.bedrag}|{t.naam_tegenpartij or ''}|{t.omschrijving or ''}"
                legacy_hash = hashlib.md5(legacy_str.encode()).hexdigest()
                
                if t.hash in existing_hashes or legacy_hash in existing_hashes:
                    duplicate_count += 1
                else:
                    unique_transactions.append(t)
                    existing_hashes.add(t.hash)
                    existing_hashes.add(legacy_hash)
            
            # Store transactions in session state before AI step
            st.session_state['current_transactions'] = unique_transactions
            
            if duplicate_count > 0:
                st.info(f"ℹ️ **{duplicate_count}** dubbele transacties zijn eruit gefilterd.")
            
            if not unique_transactions:
                st.warning("⚠️ Alle transacties in dit bestand staan al in het systeem.")
                return
                
            st.success(f"✅ {len(unique_transactions)} nieuwe transacties klaar voor analyse")
            
            # Show preview
            with st.expander("📋 Voorbeeld van ingelezen data", expanded=True):
                preview_df = pd.DataFrame([{
                    'Datum': t.datum,
                    'Bedrag': f"€{t.bedrag:,.2f}",
                    'Tegenpartij': t.naam_tegenpartij or '-'
                } for t in unique_transactions[:10]])
                st.dataframe(preview_df, use_container_width=True, hide_index=True)

            # Analyze and suggest categories using AI agent
            if st.button("AI Agent: Analyseer & Categoriseer 🤖", type="primary", use_container_width=True):
                ai_categorizer = AiCategorizer()
                
                with st.spinner("De AI agent analyseert de transacties..."):
                    # Use the stored transactions
                    txns_to_analyze = st.session_state.get('current_transactions', [])
                    if not txns_to_analyze:
                        st.error("Sessie verlopen. Upload het bestand opnieuw.")
                        return
                        
                    processed_txns = ai_categorizer.analyze_batch(txns_to_analyze)
                
                if not processed_txns:
                    st.error("❌ Er ging iets mis bij de AI-analyse. Probeer het opnieuw.")
                else:
                    st.session_state['parsed_transactions'] = processed_txns
                    st.session_state['upload_step'] = 'review_categories'
                    st.rerun()

    # Cancel button at any time during Step 1
    if st.button("❌ Annuleren & Terug naar Dashboard", use_container_width=True):
        st.session_state['page'] = 'dashboard'
        st.rerun()


def show_category_review():
    """Step 2: Review and approve AI suggested categories."""
    
    st.subheader("🤖 AI Analyse Resultaten")
    st.markdown("De AI agent heeft je transacties geanalyseerd. Hieronder zie je de voorgestelde categorisatie:")
    
    transactions = st.session_state['parsed_transactions']
    if not transactions:
        st.error("Geen transacties gevonden om te beoordelen")
        return

    # Group transactions by category for summary view
    cat_summary = {}
    for t in transactions:
        cat = t.categorie or "Overig"
        if cat not in cat_summary:
            cat_summary[cat] = {
                "count": 0,
                "total": 0,
                "confidence_avg": 0,
                "examples": []
            }
        cat_summary[cat]["count"] += 1
        cat_summary[cat]["total"] += float(t.bedrag)
        cat_summary[cat]["confidence_avg"] += (t.ai_confidence or 0.5)
        if len(cat_summary[cat]["examples"]) < 3:
            cat_summary[cat]["examples"].append(t.naam_tegenpartij)

    # Display summary cards
    for cat_name, data in cat_summary.items():
        avg_conf = data["confidence_avg"] / data["count"]
        with st.expander(f"**{cat_name}** ({data['count']} transacties | €{data['total']:,.2f})", expanded=avg_conf < 0.8):
            st.write(f"**Gemiddelde betrouwbaarheid:** {avg_conf:.1%}")
            st.write(f"**Voorbeelden:** {', '.join(data['examples'])}")
            
            # Show a few transactions with reasoning
            sub_tx = [t for t in transactions if t.categorie == cat_name][:5]
            for t in sub_tx:
                st.caption(f"📝 {t.naam_tegenpartij}: {t.ai_reasoning} (Vertrouwen: {t.ai_confidence:.0%})")

        
        st.markdown("---")
    
    # Detailed Table View
    with st.expander("🔍 Gedetailleerd Overzicht (Alle Transacties)", expanded=False):
        df_details = pd.DataFrame([{
            "Datum": t.datum,
            "Tegenpartij": t.naam_tegenpartij,
            "Bedrag": float(t.bedrag),
            "Categorie": t.categorie,
            "AI Naam": t.ai_name,
            "AI Motivatie": t.ai_reasoning,
            "Vertrouwen": t.ai_confidence,
            "Omschrijving": t.omschrijving
        } for t in transactions])
        
        # We allow editing categories here too
        db_ops = DatabaseOperations()
        user_categories = db_ops.get_categories(get_current_user().id)
        db_category_names = sorted([c['name'] for c in user_categories])
        if "Overig" not in db_category_names:
            db_category_names.append("Overig")
            
        edited_df = st.data_editor(
            df_details,
            column_config={
                "Datum": st.column_config.DateColumn("Datum", disabled=True),
                "Tegenpartij": st.column_config.TextColumn("Tegenpartij"),
                "Bedrag": st.column_config.NumberColumn("Bedrag", format="€ %.2f", disabled=True),
                "Categorie": st.column_config.SelectboxColumn("Categorie", options=db_category_names, required=True),
                "AI Naam": st.column_config.TextColumn("🤖 AI Naam", disabled=True),
                "AI Motivatie": st.column_config.TextColumn("🤖 Motivatie", disabled=True),
                "Vertrouwen": st.column_config.ProgressColumn("🤖 Vertrouwen", format="%.0f%%", min_value=0, max_value=1),
                "Omschrijving": None # Hide description
            },

            hide_index=True,
            use_container_width=True,
            key="upload_details_editor"
        )
        
        # Update session state if edited
        if st.checkbox("Wijzigingen in tabel toepassen"):
            for i, row in edited_df.iterrows():
                transactions[i].categorie = row["Categorie"]
                transactions[i].naam_tegenpartij = row["Tegenpartij"]
            st.session_state['parsed_transactions'] = transactions
            st.success("Wijzigingen opgeslagen!")

    
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
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("⬅️ Terug naar Bestand Kiezen", use_container_width=True):
            st.session_state['upload_step'] = 'upload'
            st.rerun()
    
    with col2:
        if st.button("✅ Alles Akkoord & Doorgaan", type="primary", use_container_width=True):
            st.session_state['upload_step'] = 'import'
            st.rerun()



def show_import_confirmation():
    """Step 3: Import transactions with approved categories."""
    
    user = get_current_user()
    if not user:
        st.error("Je moet ingelogd zijn")
        return
    
    transactions = st.session_state['parsed_transactions']
    
    st.subheader("💾 Importeren")
    st.info(f"Klaar om {len(transactions)} transacties te importeren met AI-verrijkte data.")

    
    # Show summary
    with st.expander("📊 Samenvatting", expanded=True):
        st.write(f"**Aantal transacties:** {len(transactions)}")
        # Count high vs low confidence
        high_conf = len([t for t in transactions if (t.ai_confidence or 0) >= 0.8])
        st.write(f"✅ Hoge betrouwbaarheid: {high_conf}")
        st.write(f"⚠️ Lage betrouwbaarheid: {len(transactions) - high_conf}")

    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("⬅️ Terug naar Categorieën", use_container_width=True):
            st.session_state['upload_step'] = 'review_categories'
            st.rerun()
    
    with col2:
        if st.button("🚀 Importeren!", type="primary", use_container_width=True):
            perform_import(transactions, user.id)

def perform_import(transactions, user_id):
    """Perform the actual import with AI metadata."""
    
    db_ops = DatabaseOperations()
    
    # Map for name -> id
    cat_name_to_id = {}
    
    with st.spinner("Categorieën worden aangemaakt..."):
        # Ensure "Overig" exists
        overig_cat = Category(name="Overig", color="#9ca3af", rules=[])
        overig_id = db_ops.create_category(overig_cat, user_id)
        cat_name_to_id["Overig"] = overig_id
        
        # Create custom categories from session state in database
        temp_cats = st.session_state.get('temp_approved_categories', {})
        for cat_name, cat_data in temp_cats.items():
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
        # Get existing categories to map IDs
        db_categories = db_ops.get_categories(user_id)
        cat_map = {cat['name']: cat['id'] for cat in db_categories}
        
        # Ensure "Overig" exists
        if "Overig" not in cat_map:
            overig_cat = Category(name="Overig", color="#9ca3af", rules=[])
            overig_id = db_ops.create_category(overig_cat, user_id)
            cat_map["Overig"] = overig_id
        
        overig_id = cat_map["Overig"]

        # Link transactions to category IDs based on AI or rule results
        for t in transactions:
            t.categorie_id = cat_map.get(t.categorie, overig_id)
                
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
