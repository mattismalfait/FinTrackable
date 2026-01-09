"""
Main dashboard interface with all visualizations and analytics.
"""
import streamlit as st
import pandas as pd
from textwrap import dedent
from datetime import datetime, timedelta, date
from database.operations import DatabaseOperations
from services.analytics import Analytics
from services.categorization import CategorizationEngine
from views.components.visualizations import (
    create_monthly_trend_chart,
    create_income_expense_chart,
    create_category_breakdown,
    create_investment_progress,
    create_year_comparison
)
from views.auth import get_current_user
from utils.ui.template_loader import load_template
from config.settings import DEFAULT_INVESTMENT_GOAL
from typing import List, Dict

@st.cache_data(ttl=300)
def get_cached_transactions(user_id: str) -> List[Dict]:
    """Fetch transactions with caching (5 mins)."""
    db = DatabaseOperations()
    # We fetch ALL transactions to handle global filtering first
    # Ideally should perform filtering at SQL level, but for <10k records this is fine
    return db.get_transactions(user_id, is_confirmed=True)

def show_dashboard():
    """Display main financial dashboard."""
    user = get_current_user()
    if not user:
        st.error("Je moet ingelogd zijn om het dashboard te bekijken")
        return

    st.title("📊 Financieel Dashboard")
    
    # Initialize database operations
    db_ops = DatabaseOperations()
    
    # Load user preferences
    preferences = db_ops.get_user_preferences(user.id)
    investment_goal = preferences.get('investment_goal_percentage', DEFAULT_INVESTMENT_GOAL) if preferences else DEFAULT_INVESTMENT_GOAL
    
    # Fetch cached transactions
    all_confirmed = get_cached_transactions(user.id)
    
    if not all_confirmed:
        show_empty_state()
        return

    # Dashboard visualizations should exclude "Lopende" transactions
    dashboard_transactions = [t for t in all_confirmed if not t.get('is_lopende_rekening', False)]
    
    # Initialize analytics - Phase 1: Global metrics (Date range detection)
    # Ideally we'd just query min/max date from DB, but using our optimized Analytics class is fast enough
    analytics_global = Analytics(dashboard_transactions)
    min_date, max_date = analytics_global.get_date_range()

    # --- TOP FILTER BAR (COMPACT) ---
    
    # Create a compact row for controls
    f_col1, f_col2, f_col3, f_col4 = st.columns([2, 1.5, 1.5, 4])
    
    with f_col1:
        view_mode = st.selectbox("Weergave", ["Maand", "Jaar", "Aangepast"], label_visibility="collapsed")
        
    start_date, end_date = min_date or date.today(), max_date or date.today()
    
    # Helper for years
    available_years = sorted(list(set(range(min_date.year, max_date.year + 1)))) if min_date and max_date else [date.today().year]
    if not available_years: available_years = [date.today().year]
    
    if view_mode == "Maand":
        with f_col2:
            selected_year = st.selectbox("Jaar", available_years, index=len(available_years)-1, label_visibility="collapsed", key="sel_year_month_mode")
        with f_col3:
            month_names = {1: "Januari", 2: "Februari", 3: "Maart", 4: "April", 5: "Mei", 6: "Juni", 
                          7: "Juli", 8: "Augustus", 9: "September", 10: "Oktober", 11: "November", 12: "December"}
            today = date.today()
            default_month = today.month if selected_year == today.year else 1
            selected_month_name = st.selectbox("Maand", list(month_names.values()), index=default_month-1, label_visibility="collapsed")
            selected_month = list(month_names.keys())[list(month_names.values()).index(selected_month_name)]
            
        import calendar
        start_date = date(selected_year, selected_month, 1)
        last_day = calendar.monthrange(selected_year, selected_month)[1]
        end_date = date(selected_year, selected_month, last_day)
        
    elif view_mode == "Jaar":
        with f_col2:
            selected_year = st.selectbox("Jaar", available_years, index=len(available_years)-1, label_visibility="collapsed", key="sel_year_year_mode")
            
        start_date = date(selected_year, 1, 1)
        end_date = date(selected_year, 12, 31)
        
    else: # Aangepast
        with f_col2:
             # Span across col 2 and 3 fordate input to have space
             pass
        with f_col2: # Actually put it in col 2 but maybe wider? 
             # Re-doing columns for this mode might be tricky if we want exact alignment, 
             # but let's try to put it in col2 and make col2 wider in the definitions if needed.
             # Or just use a different layout for custom.
             # Let's keep simpler:
             try:
                date_range = st.date_input(
                    "Bereik",
                    value=(min_date, max_date) if min_date and max_date else (date.today(), date.today()),
                    min_value=min_date if min_date else date.today(),
                    max_value=max_date if max_date else date.today(),
                    label_visibility="collapsed"
                )
                if len(date_range) == 2:
                    start_date, end_date = date_range
                elif len(date_range) == 1:
                    start_date = end_date = date_range[0]
             except:
                start_date, end_date = date.today(), date.today()
    
    date_range = (start_date, end_date)
    st.divider()

    # Sidebar filters
    with st.sidebar:
        st.header("🔍 Filters")
        
        # Date range removed from here
        
        # Category filter
        st.subheader("Selecteer Categorieën")
        user_categories = db_ops.get_categories(user.id)
        cat_engine = CategorizationEngine(user_categories)
        
        # Filter categories: Only show those defined in DB OR used in dashboard transactions
        defined_names = {c['name'] for c in user_categories}
        used_names = {t.get('categorie', 'Overig') for t in dashboard_transactions}

        all_categories = sorted(list(defined_names.union(used_names)))
        if "Overig" not in all_categories:
            all_categories.append("Overig")
            all_categories.sort()
            
        # Select All logic
        if 'select_all_cats' not in st.session_state:
            st.session_state['select_all_cats'] = True
            for cat in all_categories:
                st.session_state[f"filter_cat_{cat}"] = True
                
        def toggle_all():
            new_state = st.session_state.select_all_cats
            for cat in all_categories:
                st.session_state[f"filter_cat_{cat}"] = new_state
                
        st.checkbox("Alles selecteren", key="select_all_cats", on_change=toggle_all)
        
        selected_categories = []
        for cat in all_categories:
            if st.checkbox(cat, key=f"filter_cat_{cat}"):
                selected_categories.append(cat)
                
        # Apply filters button
        if st.button("🔄 Filters Toepassen", use_container_width=True):
            st.rerun()

        st.divider()
        st.subheader("🛠️ Systeem")
        if st.button("🧼 Duplicaten Opschonen", help="Vernieuwt de unieke codes van alle transacties en verwijdert duplicaten."):
            with st.spinner("Database wordt bijgewerkt..."):
                results = db_ops.migrate_transaction_hashes(user.id)
                if results['success'] > 0 or results['duplicates_removed'] > 0:
                    st.success(f"Klaar! {results['success']} codes vernieuwd, {results['duplicates_removed']} duplicaten verwijderd.")
                    get_cached_transactions.clear() # Clear cache after update
                    st.rerun()
                else:
                    st.info("Geen wijzigingen nodig.")
    
    # Initialize analytics - Phase 2: Active filtered view
    # Instead of mutating analytics_global, we assume filters apply.
    # We can either filter the list first OR use analytics methods.
    # Since we optimized Analytics to accept dataframes or lists, let's just 
    # rebuild it IF filters are applied.
    
    # Optimization: If no filters changed (default), assume full range.
    # But usually easier to just apply filters.
    
    current_analytics = analytics_global
    
    # Apply filters if needed
    if len(date_range) == 2:
        current_analytics.filter_by_date_range(date_range[0], date_range[1])
    
    # Apply category filter
    if len(selected_categories) != len(all_categories):
        current_analytics.filter_by_categories(selected_categories)

    # Period Label Calculation
    period_label = "Geselecteerde Periode"
    if 'view_mode' in locals():
        if view_mode == "Maand" and start_date:
            month_names_nl = ["Januari", "Februari", "Maart", "April", "Mei", "Juni", "Juli", "Augustus", "September", "Oktober", "November", "December"]
            period_label = f"{month_names_nl[start_date.month-1]} {start_date.year}"
        elif view_mode == "Jaar" and start_date:
            period_label = f"{start_date.year}"

    # Metric Row
    metrics_template = load_template("components/metrics.html")
    net_bal = current_analytics.get_net_balance()
    st.markdown(metrics_template.format(
        total_income=current_analytics.get_total_income(),
        total_expenses=current_analytics.get_total_expenses(),
        net_balance=net_bal,
        net_color="#10b981" if net_bal >= 0 else "#ef4444",
        investment_pct=current_analytics.get_investment_percentage()
    ), unsafe_allow_html=True)
    
    # Budget Comparison
    show_budget_comparison(current_analytics, user_categories, user.id, db_ops, float(investment_goal), period_label)
    
    st.divider()
    
    # Main Tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Overzicht", 
        "📈 Trends", 
        "🎯 Investeringen",
        "📅 Jaarlijks",
        "⏳ Lopende"
    ])
    
    with tab1:
        show_overview_tab(current_analytics, cat_engine)
    with tab2:
        show_trends_tab(current_analytics, cat_engine)
    with tab3:
        show_investments_tab(current_analytics, float(investment_goal))
    with tab4:
        show_yearly_tab(current_analytics)
    with tab5:
        show_lopende_rekening_tab(all_confirmed, db_ops, user.id, user_categories)

def show_overview_tab(analytics: Analytics, cat_engine: CategorizationEngine):
    """Show overview tab with income vs expenses and category breakdown."""
    st.subheader("Inkomsten vs. Uitgaven")
    monthly_totals = analytics.get_monthly_totals()
    if not monthly_totals.empty:
        fig = create_income_expense_chart(monthly_totals)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Geen data beschikbaar voor deze periode")
        
    st.divider()
    
    # Category breakdown
    col1, col2 = st.columns([2, 1])
    with col1:
        st.subheader("Uitgaven per Categorie")
        category_breakdown = analytics.get_category_breakdown(expense_only=True)
        if category_breakdown:
            category_colors = cat_engine.get_category_colors()
            fig = create_category_breakdown(category_breakdown, category_colors)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Geen uitgaven in deze periode")
            
    with col2:
        st.subheader("Top Uitgaven")
        top_expenses = analytics.get_top_transactions(n=5, by='amount')
        if top_expenses:
            item_template = load_template("components/top_expense_item.html")
            colors = cat_engine.get_category_colors()
            for trans in top_expenses:
                cat_name = trans.get('categorie', 'Overig')
                cat_color = colors.get(cat_name, "#9ca3af")
                
                display_name = trans.get('naam_tegenpartij')
                if not display_name or str(display_name).strip() in ["", "-", "--", "---", "nan", "None"]:
                    display_name = "Onbekend"
                    
                st.markdown(item_template.format(
                    cat_color=cat_color,
                    counterparty=display_name,
                    date=trans['datum'].strftime('%d %b %Y') if hasattr(trans['datum'], 'strftime') else str(trans['datum']),
                    amount=abs(float(trans['bedrag'])),
                    cat_name=cat_name
                ), unsafe_allow_html=True)
        else:
            st.info("Geen transacties")

def show_trends_tab(analytics: Analytics, cat_engine: CategorizationEngine):
    """Show trends tab with monthly breakdown by category."""
    st.subheader("Maandelijkse Trends per Categorie")
    monthly_by_category = analytics.get_monthly_by_category()
    if not monthly_by_category.empty:
        category_colors = cat_engine.get_category_colors()
        fig = create_monthly_trend_chart(monthly_by_category, category_colors)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Geen data beschikbaar voor deze periode")
        
    st.divider()
    
    # Category totals table
    st.subheader("Categorie Totalen")
    category_totals = analytics.get_category_totals()
    if category_totals:
        df = pd.DataFrame([
            {
                'Categorie': cat,
                'Bedrag': f"€{abs(amount):,.2f}",
                'Type': 'Inkomst' if amount > 0 else 'Uitgave'
            }
            for cat, amount in sorted(category_totals.items(), key=lambda x: abs(x[1]), reverse=True)
        ])
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("Geen categorieën om weer te geven")

def show_budget_comparison(analytics: Analytics, categories: list[dict], user_id: str, db_ops: DatabaseOperations, investment_goal: float, period_label: str = ""):
    """Render the budget vs actual table."""
    st.subheader("🗓️ Budget Planning & Realisatie")
    
    total_income = analytics.get_total_income()
    
    st.markdown(dedent(f"""
        <div style="background-color: #f8fafc; padding: 15px; border-radius: 10px; border-left: 5px solid #3b82f6; margin-bottom: 20px;">
            <h4 style="margin:0; color: #64748b;">Totaal Inkomen ({period_label}): <span style="color: #0f172a;">€{total_income:,.2f}</span></h4>
        </div>
    """), unsafe_allow_html=True)

    if not categories:
        st.info("Voeg eerst categorieën toe om een budget in te stellen.")
        return

    # Calculate budget data
    budget_data = []
    total_budget = 0
    total_spent = 0
    
    for cat in categories:
        cat_name = str(cat['name']).strip()
        if cat_name == "Inkomen" or cat_name == "Overig": continue
        
        pct = cat.get('percentage', 0) or 0
        if pct == 0 and cat_name == "Overig": continue
        
        budget_amt = total_income * (pct / 100)
        spent_amt = analytics.get_category_spending(cat_name)
        surplus = budget_amt - spent_amt
        
        budget_data.append({
            "id": cat['id'],
            "Categorie": cat['name'],
            "Verdeling_Raw": pct,
            "Verdeling": f"{pct}%",
            "Budget": budget_amt,
            "Uitgegeven": spent_amt,
            "Overschot": surplus
        })
        
        total_budget += budget_amt
        total_spent += spent_amt

    if budget_data:
        df_budget = pd.DataFrame(budget_data)
        # Sort: Investeren at bottom
        df_budget['sort_key'] = df_budget['Categorie'].apply(lambda x: 1 if x == "Investeren" else 0)
        df_budget = df_budget.sort_values('sort_key').drop('sort_key', axis=1).reset_index(drop=True)
        
        # Display DataFrame preparation
        display_df = df_budget.copy()
        
        for col in ["Budget", "Uitgegeven", "Overschot"]:
            display_df[col] = display_df[col].apply(lambda x: f"€{x:,.2f}")
            
        st.table(display_df[["Categorie", "Verdeling", "Budget", "Uitgegeven", "Overschot"]].style.apply(_style_budget_surplus, axis=1))

        # Totals
        total_surplus = total_budget - total_spent
        t_color = "#b91c1c" if total_surplus < 0 else "#15803d"
        t_bg = "#fee2e2" if total_surplus < 0 else "#f0fdf4"
        
        st.markdown(dedent(f"""
            <div style="display: flex; justify-content: space-between; padding: 10px; background-color: {t_bg}; border-radius: 5px; font-weight: bold; margin-top: -15px; border: 1px solid #e2e8f0;">
                <span>TOTAAL</span>
                <span style="color: {t_color};">Overschot: €{total_surplus:,.2f}</span>
            </div>
        """), unsafe_allow_html=True)
        
    # Budget Editor
    with st.expander("⚙️ Budget Verdeling Aanpassen"):
        budgetable_cats = [c for c in categories if c['name'] != "Inkomen"]
        current_total = sum(int(c.get('percentage', 0) or 0) for c in budgetable_cats)
        
        st.write(f"**Totaal Gebudgetteerd:** {current_total}%")
        if current_total > 100:
            st.warning("⚠️ Meer dan 100%!")
            st.progress(1.0)
        else:
            st.progress(current_total / 100)
            
        with st.form("budget_form"):
            new_percentages = {}
            # Responsive columns
            cols = st.columns(3)
            for i, cat in enumerate(budgetable_cats):
                with cols[i % 3]:
                    current_pct = int(investment_goal) if cat['name'] == "Investeren" else (cat.get('percentage', 0) or 0)
                    new_val = st.number_input(f"{cat['name']} (%)", min_value=0, max_value=100, value=current_pct, key=f"inp_{cat['id']}")
                    new_percentages[cat['id']] = (new_val, cat['name'])
                    
            if st.form_submit_button("✅ Verdeling Opslaan"):
                all_success = True
                inv_pct = None
                
                for cat_id, (pct, c_name) in new_percentages.items():
                    if not db_ops.update_category_percentage(cat_id, pct, user_id):
                        all_success = False
                    if c_name == "Investeren":
                        inv_pct = pct
                        
                if all_success and inv_pct is not None:
                    db_ops.create_or_update_preferences(user_id, {"investment_goal_percentage": inv_pct})
                    
                if all_success:
                    st.success("Opgeslagen!")
                    st.rerun()

def _style_budget_surplus(row):
    """Helper for budget table styling."""
    val_str = row['Overschot']
    category = row['Categorie']
    border_style = 'border-top: 2px solid #cbd5e1;' if category == "Investeren" else ''
    
    try:
        val = float(val_str.replace('€', '').replace(',', ''))
        
        style = ''
        target_col_idx = 4 # Overschot is the 5th column
        
        # Investeren logic: Surplus (underspending) is BAD.
        if category == "Investeren":
            if val > 0: # Underspent
                style = 'background-color: #fee2e2; color: #b91c1c; font-weight: bold;'
            else:
                style = 'color: #15803d;'
        else:
            if val < 0: # Overspent
                style = 'background-color: #fee2e2; color: #b91c1c; font-weight: bold;'
            else:
                style = 'color: #15803d;'
                
        base_styles = [border_style] * 5
        base_styles[4] += f" {style}"
        return base_styles
    except:
        return [border_style] * 5

def show_investments_tab(analytics: Analytics, investment_goal: float):
    """Show investments tab with goal tracking."""
    st.subheader("Investeringsdoelen Tracking")
    current_pct = analytics.get_investment_percentage()
    
    col1, col2 = st.columns([1, 1])
    with col1:
        fig = create_investment_progress(current_pct, investment_goal)
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        st.markdown("### 📊 Analyse")
        total_income = analytics.get_total_income()
        cat_totals = analytics.get_category_totals()
        investments = abs(cat_totals.get('Investeren', 0))
        
        st.metric("Totaal Inkomen", f"€{total_income:,.2f}")
        st.metric("Totaal Geïnvesteerd", f"€{investments:,.2f}")
        st.metric("Percentage", f"{current_pct:.1f}%")
        st.divider()
        
        if current_pct >= investment_goal:
            st.success(f"✅ Je hebt je doel van {investment_goal}% bereikt!")
        else:
            remaining = (investment_goal / 100 * total_income) - investments
            st.warning(f"⚠️ Nog €{remaining:,.2f} nodig om je doel te bereiken")

def show_yearly_tab(analytics: Analytics):
    """Show yearly comparison tab."""
    st.subheader("Jaarlijkse Vergelijking")
    yearly_data = analytics.get_year_over_year_comparison()
    
    if yearly_data:
        fig = create_year_comparison(yearly_data)
        st.plotly_chart(fig, use_container_width=True)
        st.divider()
        
        st.subheader("Jaarlijks Overzicht")
        df = pd.DataFrame([
            {
                'Jaar': year,
                'Inkomsten': f"€{data['income']:,.2f}",
                'Uitgaven': f"€{data['expenses']:,.2f}",
                'Netto': f"€{data['net']:,.2f}",
                'Investeringen %': f"{data['investment_pct']:.1f}%"
            }
            for year, data in sorted(yearly_data.items(), reverse=True)
        ])
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("Niet genoeg data")

def show_lopende_rekening_tab(all_transactions: list, db_ops: DatabaseOperations, user_id: str, categories: list):
    """Show transactions marked as Lopende Rekening."""
    st.subheader("⏳ Lopende Rekening")
    st.caption("Transacties die zijn gemarkeerd om terugbetaald te worden.")
    
    lopende_trans = [t for t in all_transactions if t.get('is_lopende_rekening', False)]
    if not lopende_trans:
        st.info("Geen openstaande posten gevonden.")
        # Note: Removed "return" to allow bulk actions (though empty list makes them useless) 
        # but let's just return for cleaner UI
        return

    # Summary metric
    total_open = sum(float(t['bedrag']) for t in lopende_trans)
    st.metric("Totaal openstaand", f"€{total_open:,.2f}")
    st.divider()
    
    cat_engine = CategorizationEngine(categories)
    # STRICTLY use DB categories
    db_category_names = sorted([c['name'] for c in categories])
    if "Overig" not in db_category_names:
        db_category_names.append("Overig")
    cat_name_to_id = {c['name']: c['id'] for c in categories}
    
    # Prepare DataFrame for editor
    df_data = []
    for t in lopende_trans:
        display_name = t.get('naam_tegenpartij', 'Onbekend')
        if not display_name or str(display_name).strip() in ["", "-", "nan"]:
             display_name = "Onbekend"
             
        df_data.append({
            "Select": False,
            "Datum": t['datum'], # Already datetime/date from analytics processing or raw string? 
                                 # get_transactions now returns list of dicts. 
                                 # If cached, they are regular dicts.
                                 # We need to ensure date type for editor.
            "Tegenpartij": display_name,
            "Bedrag": float(t['bedrag']),
            "Categorie": t.get('categorie', 'Overig'),
            "Lopende": True,
            "Omschrijving": t.get('omschrijving', '') or "",
            "AI Naam": t.get('ai_name', ''),
            "AI Motivatie": t.get('ai_reasoning', ''),
            "Vertrouwen": float(t.get('ai_confidence') or 0.0),
            "id": t['id']
        })


        
    df = pd.DataFrame(df_data)
    # Ensure Datum is date object
    df['Datum'] = pd.to_datetime(df['Datum']).dt.date

    # --- Session State Management for Data Editor ---
    if 'lopende_df_state' not in st.session_state:
        st.session_state.lopende_df_state = df.copy()
    else:
        # Detect external changes (e.g. from DB update)
        current_ids = set(df['id'])
        state_ids = set(st.session_state.lopende_df_state['id'])
        if current_ids != state_ids:
            st.session_state.lopende_df_state = df.copy()
            if 'editor_lopende' in st.session_state:
                 del st.session_state.editor_lopende

    # 🔍 Search and Filter UI for Lopende
    col_search_l, col_cat_l = st.columns([3, 1.5])
    with col_search_l:
        search_l = st.text_input("🔍 Broad Search", placeholder="Zoek op naam, omschrijving...", key="lop_search", label_visibility="collapsed")
    with col_cat_l:
        cat_options_l = ["Alle Categorieën"] + db_category_names
        cat_filter_l = st.selectbox("Category Filter", options=cat_options_l, key="lop_cat_filter", label_visibility="collapsed")

    filtered_lop = st.session_state.lopende_df_state.copy()
    if search_l:
        q = search_l.lower()
        mask = (
            filtered_lop['Tegenpartij'].str.lower().str.contains(q, na=False) |
            filtered_lop['Categorie'].str.lower().str.contains(q, na=False) |
            filtered_lop['Omschrijving'].str.lower().str.contains(q, na=False)
        )
        filtered_lop = filtered_lop[mask]
    
    if cat_filter_l != "Alle Categorieën":
        filtered_lop = filtered_lop[filtered_lop['Categorie'] == cat_filter_l]

    # Handle Edits (Updated for filtered view tracking)
    if 'editor_lopende' in st.session_state and 'edited_rows' in st.session_state.editor_lopende:
        edits = st.session_state.editor_lopende['edited_rows']
        if edits:
            for row_pos_str, row_changes in edits.items():
                pos = int(row_pos_str)
                if pos >= len(filtered_lop): continue
                
                idx = filtered_lop.index[pos]
                trans_id = filtered_lop.at[idx, 'id']

                # Update local state (full state)
                for col, val in row_changes.items():
                    st.session_state.lopende_df_state.at[idx, col] = val
                    
                    if col == "Categorie" and st.session_state.lopende_df_state.at[idx, "Select"]:
                        new_cat = val
                        for other_idx in st.session_state.lopende_df_state.index:
                            if st.session_state.lopende_df_state.at[other_idx, "Select"] and other_idx != idx:
                                    st.session_state.lopende_df_state.at[other_idx, "Categorie"] = new_cat
                                    cid = cat_name_to_id.get(new_cat)
                                    if cid:
                                        db_ops.update_transaction(st.session_state.lopende_df_state.at[other_idx, 'id'], 
                                                                {"categorie_id": cid}, user_id)
                # Sync to DB
                row = st.session_state.lopende_df_state.loc[idx]
                cid = cat_name_to_id.get(row['Categorie'])
                updates = {
                    "datum": str(row['Datum']),
                    "bedrag": float(row['Bedrag']),
                    "naam_tegenpartij": str(row['Tegenpartij']),
                    "omschrijving": str(row['Omschrijving']),
                    "categorie_id": cid,
                    "is_lopende_rekening": bool(row['Lopende'])
                }
                db_ops.update_transaction(trans_id, updates, user_id)
                
                if 'Lopende' in row_changes and not row_changes['Lopende']:
                    get_cached_transactions.clear()
                    st.rerun()
            st.rerun()

    # Dynamic Height
    height = (len(filtered_lop) * 35) + 50
    
    # Bulk Actions (Moved Top)
    selected_rows = filtered_lop[filtered_lop['Select']]
    
    col_sel_l, col_desel_l, col_del_l, col_ai_l = st.columns([1.5, 1.5, 2, 2])
    with col_sel_l:
        if st.button("✅ Alles", key="btn_sel_lop_all", use_container_width=True):
            st.session_state.lopende_df_state.loc[filtered_lop.index, 'Select'] = True
            st.rerun()
    with col_desel_l:
        if st.button("❌ Niets", key="btn_desel_lop_all", use_container_width=True):
            st.session_state.lopende_df_state.loc[filtered_lop.index, 'Select'] = False
            st.rerun()

    with col_del_l:
        if not selected_rows.empty:
            if st.button(f"🗑️ Verwijder ({len(selected_rows)})", type="primary", use_container_width=True, key="btn_del_lop_top"):
                count = 0
                for tid in selected_rows['id']:
                     if db_ops.update_transaction(tid, {"is_lopende_rekening": False}, user_id):
                         count += 1
                if count > 0:
                    st.success(f"{count} transacties bijgewerkt.")
                    get_cached_transactions.clear()
                    st.rerun()
        else:
            st.button(f"🗑️ Verwijder", type="primary", use_container_width=True, disabled=True, key="btn_del_lop_dis")
    
    with col_ai_l:
        if not selected_rows.empty:
            if st.button("🤖 AI Optimaliseer", use_container_width=True, key="btn_ai_lop_top"):
                from services.ai_categorizer import AiCategorizer
                from models.transaction import Transaction
                ai_categorizer = AiCategorizer()
                if not ai_categorizer.enabled:
                    st.error("AI agent niet geconfigureerd.")
                else:
                    with st.spinner("AI analyseert..."):
                        user_categories = db_ops.get_categories(user_id)
                        ai_categorizer.set_categories(user_categories)
                        cat_name_to_id = {c['name']: c['id'] for c in user_categories}

                        tx_objs = []
                        for _, r in selected_rows.iterrows():
                            tx = Transaction(id=r['id'], datum=r['Datum'], bedrag=Decimal(str(r['Bedrag'])),
                                            naam_tegenpartij=r['Tegenpartij'], omschrijving=r.get('Omschrijving', ''))
                            tx_objs.append(tx)
                        
                        optimized_txs = ai_categorizer.analyze_batch(tx_objs)
                        
                        for tx in optimized_txs:
                            c_id = cat_name_to_id.get(tx.categorie)
                            updates = {"naam_tegenpartij": tx.naam_tegenpartij, "categorie_id": c_id,
                                      "ai_name": tx.ai_name, "ai_reasoning": tx.ai_reasoning, "ai_confidence": tx.ai_confidence}
                            db_ops.update_transaction(tx.id, updates, user_id)
                        
                        st.success(f"✅ {len(optimized_txs)} geoptimaliseerd!")
                        get_cached_transactions.clear()
                        st.rerun()
        else:
             st.button("🤖 AI Optimaliseer", use_container_width=True, disabled=True, key="btn_ai_lop_dis")

    # Display Editor
    edited_df = st.data_editor(
        filtered_lop,
        column_config={
            "Select": st.column_config.CheckboxColumn("✅", width="small", default=False),
            "Datum": st.column_config.DateColumn("Datum", format="DD-MM-YYYY"),
            "Tegenpartij": st.column_config.TextColumn("Tegenpartij"),
            "Bedrag": st.column_config.NumberColumn("Bedrag", format="€ %.2f"),
            "Categorie": st.column_config.SelectboxColumn("Categorie", options=db_category_names, required=True),
            "Lopende": st.column_config.CheckboxColumn("⏳", default=True),
            "Omschrijving": None, # Hide description
            "AI Naam": st.column_config.TextColumn("🤖 AI Naam", disabled=True),

            "AI Motivatie": st.column_config.TextColumn("🤖 Motivatie", disabled=True),
            "Vertrouwen": st.column_config.ProgressColumn("🤖 Vertrouwen", format="%.0f%%", min_value=0, max_value=1),
            "id": None
        },

        hide_index=True,
        use_container_width=True,
        height=height,
        key="editor_lopende"
    )



def show_empty_state():
    """Show empty state when no transactions exist."""
    st.info("📭 Je hebt nog geen transacties geïmporteerd")
    st.markdown("""
    ### Aan de slag
    1. **Upload je CSV**: Ga naar de 'CSV Importeren' pagina
    2. **Selecteer je KBC bankafschrift**: Kies een CSV-bestand
    3. **Controleer en importeer**: De transacties worden automatisch gecategoriseerd
    4. **Bekijk je dashboard**: Kom terug hier om je financiële overzicht te zien
    """)
    if st.button("📤 Ga naar CSV Importeren", type="primary"):
        st.session_state['page'] = 'upload'
        st.rerun()
