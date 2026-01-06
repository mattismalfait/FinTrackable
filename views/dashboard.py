"""
Main dashboard interface with all visualizations and analytics.
"""

import streamlit as st
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
    investment_goal = preferences['investment_goal_percentage'] if preferences else DEFAULT_INVESTMENT_GOAL
    
    # Fetch all transactions
    transactions = db_ops.get_transactions(user.id)
    
    if not transactions:
        show_empty_state()
        return
    
    # Initialize analytics
    analytics = Analytics(transactions)
    
    # Get date range
    min_date, max_date = analytics.get_date_range()
    
    # Sidebar filters
    with st.sidebar:
        st.header("🔍 Filters")
        
        # Date range filter
        st.subheader("Datum Bereik")
        date_range = st.date_input(
            "Selecteer periode",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date
        )
        
        # Category filter
        st.subheader("Selecteer Categorieën")
        user_categories = db_ops.get_categories(user.id)
        cat_engine = CategorizationEngine(user_categories)
        all_categories = sorted(cat_engine.get_category_names())
        
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
            if len(date_range) == 2:
                analytics.filter_by_date_range(date_range[0], date_range[1])
            analytics.filter_by_categories(selected_categories)
            st.rerun()
    
    # Apply initial filters
    if len(date_range) == 2:
        analytics_filtered = Analytics(transactions)
        analytics_filtered.filter_by_date_range(date_range[0], date_range[1])
        analytics_filtered.filter_by_categories(selected_categories)
        analytics = analytics_filtered
    
    # Key Metrics Row with Custom HTML
    metrics_template = load_template("components/metrics.html")
    st.markdown(metrics_template.format(
        total_income=analytics.get_total_income(),
        total_expenses=analytics.get_total_expenses(),
        net_balance=analytics.get_net_balance(),
        net_color="#10b981" if analytics.get_net_balance() >= 0 else "#ef4444",
        investment_pct=analytics.get_investment_percentage()
    ), unsafe_allow_html=True)
    
    st.divider()
    
    # Main visualizations
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Overzicht", 
        "📈 Trends", 
        "🎯 Investeringen",
        "📅 Jaarlijks"
    ])
    
    with tab1:
        show_overview_tab(analytics, cat_engine)
    
    with tab2:
        show_trends_tab(analytics, cat_engine)
    
    with tab3:
        show_investments_tab(analytics, investment_goal)
    
    with tab4:
        show_yearly_tab(analytics)

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
            for trans in top_expenses:
                cat_name = trans.get('categorie', 'Overig')
                cat_color = cat_engine.get_category_colors().get(cat_name, "#9ca3af")
                
                display_name = trans.get('naam_tegenpartij')
                if not display_name or display_name.strip() in ["", "-", "--", "---"]:
                    display_name = "Onbekend"
                
                st.markdown(item_template.format(
                    cat_color=cat_color,
                    counterparty=display_name,
                    date=trans['datum'].strftime('%d %b %Y'),
                    amount=abs(trans['bedrag']),
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
        import pandas as pd
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
        category_totals = analytics.get_category_totals()
        investments = abs(category_totals.get('Investeren', 0))
        
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
    
    if yearly_data and len(yearly_data) > 0:
        fig = create_year_comparison(yearly_data)
        st.plotly_chart(fig, use_container_width=True)
        
        st.divider()
        
        # Yearly breakdown table
        st.subheader("Jaarlijks Overzicht")
        import pandas as pd
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
        st.info("Niet genoeg data voor jaarlijkse vergelijking")

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
