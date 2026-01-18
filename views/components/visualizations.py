"""
Reusable visualization components using Plotly.
"""

import plotly.graph_objects as go
import plotly.express as px
from typing import Dict, List
import pandas as pd
from config.settings import CHART_CONFIG, THEME_COLORS

def create_monthly_trend_chart(monthly_by_category: pd.DataFrame, category_colors: Dict[str, str]) -> go.Figure:
    """
    Create stacked bar chart showing monthly trends by category.
    
    Args:
        monthly_by_category: DataFrame with month, categorie, total columns
        category_colors: Dict mapping category names to colors
        
    Returns:
        Plotly Figure
    """
    if monthly_by_category.empty:
        return go.Figure().add_annotation(
            text="Geen data beschikbaar",
            showarrow=False,
            font=dict(size=20)
        )
    
    # Pivot data for stacked bar chart
    pivot_df = monthly_by_category.pivot(index='month', columns='categorie', values='total').fillna(0)
    
    fig = go.Figure()
    
    for category in pivot_df.columns:
        fig.add_trace(go.Bar(
            name=category,
            x=pivot_df.index,
            y=pivot_df[category],  # Allow negative values to plot downwards
            marker_color=category_colors.get(category, '#9ca3af'),
            hovertemplate='<b>%{fullData.name}</b><br>%{y:,.2f}<extra></extra>'
        ))
    
    fig.update_layout(
        title="Maandelijkse Trends per Categorie",
        barmode='relative', # Positive up, negative down
        xaxis_title="Maand",
        yaxis_title="Bedrag ()",
        hovermode='x unified',
        height=CHART_CONFIG['height'],
        font=dict(family=CHART_CONFIG['font_family']),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    
    return fig

def create_income_expense_chart(monthly_totals: pd.DataFrame) -> go.Figure:
    """
    Create grouped bar chart for income vs expenses with net line.
    
    Args:
        monthly_totals: DataFrame with month, income, expenses, net columns
        
    Returns:
        Plotly Figure
    """
    if monthly_totals.empty:
        return go.Figure().add_annotation(
            text="Geen data beschikbaar",
            showarrow=False,
            font=dict(size=20)
        )
    
    fig = go.Figure()
    
    # Income bars
    fig.add_trace(go.Bar(
        name='Inkomsten',
        x=monthly_totals['month'],
        y=monthly_totals['income'],
        marker_color=THEME_COLORS['income'],
        hovertemplate='<b>Inkomsten</b><br>%{y:,.2f}<extra></extra>'
    ))
    
    # Expense bars
    fig.add_trace(go.Bar(
        name='Uitgaven',
        x=monthly_totals['month'],
        y=-monthly_totals['expenses'], # Negate to show below x-axis
        marker_color=THEME_COLORS['expense'],
        hovertemplate='<b>Uitgaven</b><br>%{y:,.2f}<extra></extra>'
    ))
    
    # Net line
    fig.add_trace(go.Scatter(
        name='Netto',
        x=monthly_totals['month'],
        y=monthly_totals['net'],
        mode='lines+markers',
        marker=dict(size=8, color=THEME_COLORS['success']),
        line=dict(width=3, color=THEME_COLORS['success']),
        hovertemplate='<b>Netto</b><br>%{y:,.2f}<extra></extra>'
    ))
    
    fig.update_layout(
        title="Inkomsten vs. Uitgaven",
        barmode='group',
        xaxis_title="Maand",
        yaxis_title="Bedrag ()",
        hovermode='x unified',
        height=CHART_CONFIG['height'],
        font=dict(family=CHART_CONFIG['font_family']),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    
    return fig

def create_category_breakdown(category_totals: Dict[str, float], category_colors: Dict[str, str]) -> go.Figure:
    """
    Create donut chart for category breakdown.
    
    Args:
        category_totals: Dict mapping category to total amount
        category_colors: Dict mapping category names to colors
        
    Returns:
        Plotly Figure
    """
    if not category_totals:
        return go.Figure().add_annotation(
            text="Geen data beschikbaar",
            showarrow=False,
            font=dict(size=20)
        )
    
    # Prepare data
    labels = list(category_totals.keys())
    values = [abs(v) for v in category_totals.values()]  # Use absolute values
    colors = [category_colors.get(label, '#9ca3af') for label in labels]
    
    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=0.4,
        marker=dict(colors=colors),
        textinfo='label+percent',
        hovertemplate='<b>%{label}</b><br>%{value:,.2f}<br>%{percent}<extra></extra>'
    )])
    
    fig.update_layout(
        title="Uitgaven per Categorie",
        height=CHART_CONFIG['height'],
        font=dict(family=CHART_CONFIG['font_family']),
        showlegend=True,
        legend=dict(orientation="v", yanchor="middle", y=0.5),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    
    return fig

def create_investment_progress(current_percentage: float, goal_percentage: float) -> go.Figure:
    """
    Create gauge chart for investment goal tracking.
    
    Args:
        current_percentage: Current investment percentage
        goal_percentage: Target investment percentage
        
    Returns:
        Plotly Figure
    """
    # Determine color based on achievement
    if current_percentage >= goal_percentage:
        color = THEME_COLORS['success']
    elif current_percentage >= goal_percentage * 0.7:
        color = THEME_COLORS['warning']
    else:
        color = THEME_COLORS['danger']
    
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=current_percentage,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': f"Investeringsdoel: {goal_percentage}%"},
        delta={'reference': goal_percentage},
        gauge={
            'axis': {'range': [None, 100]},
            'bar': {'color': color},
            'steps': [
                {'range': [0, goal_percentage * 0.5], 'color': "lightgray"},
                {'range': [goal_percentage * 0.5, goal_percentage], 'color': "gray"}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': goal_percentage
            }
        }
    ))
    
    fig.update_layout(
        height=300,
        font=dict(family=CHART_CONFIG['font_family']),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    
    return fig

def create_year_comparison(yearly_data: Dict[int, Dict[str, float]]) -> go.Figure:
    """
    Create grouped bar chart for year-over-year comparison.
    
    Args:
        yearly_data: Dict mapping year to {income, expenses, net, investment_pct}
        
    Returns:
        Plotly Figure
    """
    if not yearly_data:
        return go.Figure().add_annotation(
            text="Geen data beschikbaar",
            showarrow=False,
            font=dict(size=20)
        )
    
    years = sorted(yearly_data.keys())
    income_values = [yearly_data[year]['income'] for year in years]
    expense_values = [yearly_data[year]['expenses'] for year in years]
    net_values = [yearly_data[year]['net'] for year in years]
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        name='Inkomsten',
        x=years,
        y=income_values,
        marker_color=THEME_COLORS['income'],
        hovertemplate='<b>Inkomsten</b><br>%{y:,.2f}<extra></extra>'
    ))
    
    fig.add_trace(go.Bar(
        name='Uitgaven',
        x=years,
        y=[-x for x in expense_values], # Negate to show below x-axis
        marker_color=THEME_COLORS['expense'],
        hovertemplate='<b>Uitgaven</b><br>%{y:,.2f}<extra></extra>'
    ))
    
    fig.add_trace(go.Scatter(
        name='Netto',
        x=years,
        y=net_values,
        mode='lines+markers',
        marker=dict(size=10, color=THEME_COLORS['success']),
        line=dict(width=3, color=THEME_COLORS['success']),
        yaxis='y2',
        hovertemplate='<b>Netto</b><br>%{y:,.2f}<extra></extra>'
    ))
    
    fig.update_layout(
        title="Jaarlijkse Vergelijking",
        barmode='group',
        xaxis_title="Jaar",
        yaxis_title="Bedrag ()",
        yaxis2=dict(
            title="Netto ()",
            overlaying='y',
            side='right'
        ),
        hovermode='x unified',
        height=CHART_CONFIG['height'],
        font=dict(family=CHART_CONFIG['font_family']),
        showlegend=True,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    
    return fig
