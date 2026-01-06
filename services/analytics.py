"""
Analytics service for financial data aggregation and calculations.
"""

import pandas as pd
from typing import List, Dict, Optional
from datetime import date, datetime
from decimal import Decimal
from collections import defaultdict
import calendar

class Analytics:
    """Financial analytics and aggregation calculations."""
    
    def __init__(self, transactions: List[Dict]):
        """
        Initialize analytics with transaction data.
        
        Args:
            transactions: List of transaction dictionaries from database
        """
        self.df = pd.DataFrame(transactions) if transactions else pd.DataFrame()
        
        if not self.df.empty:
            # Convert datum to datetime
            self.df['datum'] = pd.to_datetime(self.df['datum'])
            # Convert bedrag to float
            self.df['bedrag'] = self.df['bedrag'].astype(float)
            # Extract month and year
            self.df['month'] = self.df['datum'].dt.to_period('M')
            self.df['year'] = self.df['datum'].dt.year
    
    def get_total_income(self) -> float:
        """Get total income (positive transactions)."""
        if self.df.empty:
            return 0.0
        return float(self.df[self.df['bedrag'] > 0]['bedrag'].sum())
    
    def get_total_expenses(self) -> float:
        """Get total expenses (negative transactions, as positive number)."""
        if self.df.empty:
            return 0.0
        return abs(float(self.df[self.df['bedrag'] < 0]['bedrag'].sum()))
    
    def get_net_balance(self) -> float:
        """Get net balance (income - expenses)."""
        return self.get_total_income() - self.get_total_expenses()
    
    def get_category_totals(self) -> Dict[str, float]:
        """
        Get total spending/income per category.
        
        Returns:
            Dict mapping category name to total amount
        """
        if self.df.empty:
            return {}
        
        category_totals = self.df.groupby('categorie')['bedrag'].sum().to_dict()
        return {k: float(v) for k, v in category_totals.items()}
    
    def get_monthly_totals(self) -> pd.DataFrame:
        """
        Get monthly aggregates.
        
        Returns:
            DataFrame with columns: month, income, expenses, net
        """
        if self.df.empty:
            return pd.DataFrame(columns=['month', 'income', 'expenses', 'net'])
        
        monthly = self.df.groupby('month').apply(
            lambda x: pd.Series({
                'income': float(x[x['bedrag'] > 0]['bedrag'].sum()),
                'expenses': abs(float(x[x['bedrag'] < 0]['bedrag'].sum())),
            })
        ).reset_index()
        
        monthly['net'] = monthly['income'] - monthly['expenses']
        monthly['month'] = monthly['month'].astype(str)
        
        return monthly
    
    def get_monthly_by_category(self) -> pd.DataFrame:
        """
        Get monthly totals broken down by category.
        
        Returns:
            DataFrame with month, category, and total
        """
        if self.df.empty:
            return pd.DataFrame(columns=['month', 'categorie', 'total'])
        
        monthly_cat = self.df.groupby(['month', 'categorie'])['bedrag'].sum().reset_index()
        monthly_cat.columns = ['month', 'categorie', 'total']
        monthly_cat['month'] = monthly_cat['month'].astype(str)
        monthly_cat['total'] = monthly_cat['total'].astype(float)
        
        return monthly_cat
    
    def get_investment_percentage(self) -> float:
        """
        Calculate percentage of income going to investments.
        
        Returns:
            Percentage (0-100)
        """
        total_income = self.get_total_income()
        if total_income == 0:
            return 0.0
        
        if self.df.empty:
            return 0.0
        
        # Get investments (assuming "Investeren" category)
        investments = self.df[self.df['categorie'] == 'Investeren']['bedrag'].sum()
        investments = abs(float(investments))  # Make positive if negative
        
        return (investments / total_income) * 100
    
    def get_year_over_year_comparison(self) -> Dict[int, Dict[str, float]]:
        """
        Get yearly comparison data.
        
        Returns:
            Dict mapping year to {income, expenses, net, investment_pct}
        """
        if self.df.empty:
            return {}
        
        yearly_data = {}
        
        for year in self.df['year'].unique():
            year_df = self.df[self.df['year'] == year]
            
            income = float(year_df[year_df['bedrag'] > 0]['bedrag'].sum())
            expenses = abs(float(year_df[year_df['bedrag'] < 0]['bedrag'].sum()))
            net = income - expenses
            
            # Investment percentage
            investments = abs(float(year_df[year_df['categorie'] == 'Investeren']['bedrag'].sum()))
            investment_pct = (investments / income * 100) if income > 0 else 0
            
            yearly_data[int(year)] = {
                'income': income,
                'expenses': expenses,
                'net': net,
                'investment_pct': investment_pct
            }
        
        return yearly_data
    
    def get_category_breakdown(self, expense_only: bool = True) -> Dict[str, float]:
        """
        Get category breakdown for pie/donut chart.
        
        Args:
            expense_only: If True, only include expense categories (negative amounts)
            
        Returns:
            Dict of category: absolute amount
        """
        if self.df.empty:
            return {}
        
        if expense_only:
            df_subset = self.df[self.df['bedrag'] < 0].copy()
        else:
            df_subset = self.df.copy()
        
        df_subset['bedrag_abs'] = df_subset['bedrag'].abs()
        breakdown = df_subset.groupby('categorie')['bedrag_abs'].sum().to_dict()
        
        return {k: float(v) for k, v in breakdown.items()}
    
    def get_date_range(self) -> tuple:
        """
        Get the date range of transactions.
        
        Returns:
            Tuple of (min_date, max_date)
        """
        if self.df.empty:
            return (None, None)
        
        return (self.df['datum'].min().date(), self.df['datum'].max().date())
    
    def filter_by_date_range(self, start_date: date, end_date: date):
        """
        Filter transactions by date range in place.
        
        Args:
            start_date: Start date
            end_date: End date
        """
        if not self.df.empty:
            mask = (self.df['datum'].dt.date >= start_date) & (self.df['datum'].dt.date <= end_date)
            self.df = self.df[mask]
    
    def filter_by_categories(self, categories: List[str]):
        """
        Filter transactions by categories in place.
        
        Args:
            categories: List of category names to include
        """
        if not self.df.empty and categories:
            self.df = self.df[self.df['categorie'].isin(categories)]
    
    def get_top_transactions(self, n: int = 10, by: str = 'amount') -> List[Dict]:
        """
        Get top N transactions.
        
        Args:
            n: Number of transactions to return
            by: Sort by 'amount' or 'date'
            
        Returns:
            List of transaction dictionaries
        """
        if self.df.empty:
            return []
        
        if by == 'amount':
            sorted_df = self.df.sort_values('bedrag', ascending=True).head(n)
        else:
            sorted_df = self.df.sort_values('datum', ascending=False).head(n)
        
        return sorted_df.to_dict('records')
