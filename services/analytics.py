"""
Analytics service for financial data aggregation and calculations.
"""

import pandas as pd
from typing import List, Dict, Optional, Tuple
from datetime import date, datetime
from functools import lru_cache, cached_property
from decimal import Decimal

class Analytics:
    """Financial analytics and aggregation calculations."""
    
    def __init__(self, transactions: List[Dict]):
        """
        Initialize analytics with transaction data.
        
        Args:
            transactions: List of transaction dictionaries from database
        """
        # Optimize DataFrame creation
        if not transactions:
            self.df = pd.DataFrame(columns=['id', 'datum', 'bedrag', 'categorie', 'naam_tegenpartij', 'omschrijving'])
        else:
            self.df = pd.DataFrame(transactions)
        
        if not self.df.empty:
            # Vectorized conversions are faster
            self.df['datum'] = pd.to_datetime(self.df['datum'])
            self.df['bedrag'] = pd.to_numeric(self.df['bedrag'], errors='coerce').fillna(0.0)
            
            # Normalize category names
            if 'categorie' in self.df.columns:
                self.df['categorie'] = self.df['categorie'].fillna('Overig').astype(str).str.strip()
            else:
                self.df['categorie'] = 'Overig'
                
            # Extract month and year efficiently
            self.df['month'] = self.df['datum'].dt.to_period('M')
            self.df['year'] = self.df['datum'].dt.year

    @cached_property
    def _positive_transactions(self) -> pd.DataFrame:
        """Cached view of positive transactions."""
        return self.df[self.df['bedrag'] > 0] if not self.df.empty else self.df

    @cached_property
    def _negative_transactions(self) -> pd.DataFrame:
        """Cached view of negative transactions."""
        return self.df[self.df['bedrag'] < 0] if not self.df.empty else self.df

    @lru_cache(maxsize=1)
    def get_total_income(self) -> float:
        """
        Get total income. 
        Strictly defined as the net sum of transactions in the 'Inkomen' category.
        """
        if self.df.empty:
            return 0.0
        
        # Filter strictly for 'Inkomen'
        # We assume category names are normalized/stripped in __init__
        income_val = self.df[self.df['categorie'] == 'Inkomen']['bedrag'].sum()
        return float(income_val)
    
    @lru_cache(maxsize=1)
    def get_total_expenses(self) -> float:
        """
        Get total expenses.
         Calculated as: Total Income - Net Balance.
         This effectively treats it as 'Net Expenses' where refunds reduce the expense total.
        """
        # Expenses is usually displayed as a positive number
        # Income - Expenses = Net  =>  Expenses = Income - Net
        return self.get_total_income() - self.get_net_balance()
    
    def get_net_balance(self) -> float:
        """Get true net balance (sum of all transactions)."""
        if self.df.empty:
            return 0.0
        return float(self.df['bedrag'].sum())
    
    @lru_cache(maxsize=1)
    def get_category_totals(self) -> Dict[str, float]:
        """
        Get total spending/income per category (net).
        
        Returns:
            Dict mapping category name to total amount
        """
        if self.df.empty:
            return {}
        
        category_totals = self.df.groupby('categorie')['bedrag'].sum()
        return category_totals.to_dict()
    
    def get_category_spending(self, category_name: str) -> float:
        """
        Get gross spending (sum of negative amounts only) for a category.
        
        Args:
            category_name: Name of the category
            
        Returns:
            Total absolute spending amount
        """
        if self.df.empty:
            return 0.0
        
        if self.df.empty:
            return 0.0
        
        # Calculate NET amount for this category
        # If I spent 100 and got 20 back, sum is -80. Spending is 80.
        # If I got 100 income, sum is 100. Spending is 0 (or -100?) -> Let's assume spending is 0 for net positive.
        
        mask = (self.df['categorie'] == category_name)
        net_val = self.df.loc[mask, 'bedrag'].sum()
        
        if net_val < 0:
            return abs(float(net_val))
        return 0.0

    @lru_cache(maxsize=1)
    def get_monthly_totals(self) -> pd.DataFrame:
        """
        Get monthly aggregates.
        
        Returns:
            DataFrame with columns: month, income, expenses, net
        """
        if self.df.empty:
            return pd.DataFrame(columns=['month', 'income', 'expenses', 'net'])
        
        # Optimized groupby without apply(lambda)
        monthly_groups = self.df.groupby('month')
        
        # Calculate income (sum of positive) and expenses (sum of negative)
        # We can do this by first separating, then grouping
        
        income_series = self.df[self.df['bedrag'] > 0].groupby('month')['bedrag'].sum()
        expenses_series = self.df[self.df['bedrag'] < 0].groupby('month')['bedrag'].sum()
        
        # Combine into DataFrame
        monthly = pd.DataFrame({
            'income': income_series,
            'expenses': expenses_series.abs() # store as positive
        }).fillna(0.0)
        
        monthly = monthly.reset_index()
        monthly['net'] = monthly['income'] - monthly['expenses']
        monthly['month'] = monthly['month'].astype(str)
        
        return monthly
    
    @lru_cache(maxsize=1)
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
    
    @lru_cache(maxsize=1)
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
        investments_mask = self.df['categorie'] == 'Investeren'
        investments = self.df.loc[investments_mask, 'bedrag'].sum()
        investments = abs(float(investments))  # Make positive if negative
        
        return (investments / total_income) * 100
    
    @lru_cache(maxsize=1)
    def get_year_over_year_comparison(self) -> Dict[int, Dict[str, float]]:
        """
        Get yearly comparison data.
        
        Returns:
            Dict mapping year to {income, expenses, net, investment_pct}
        """
        if self.df.empty:
            return {}
        
        yearly_data = {}
        
        # Optimize by doing one groupby instead of filtering in a loop
        yearly_groups = self.df.groupby('year')
        
        for year, group in yearly_groups:
            income = float(group[group['bedrag'] > 0]['bedrag'].sum())
            expenses = abs(float(group[group['bedrag'] < 0]['bedrag'].sum()))
            net = income - expenses
            
            # Investment percentage
            investments = abs(float(group[group['categorie'] == 'Investeren']['bedrag'].sum()))
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
        
        # Calculate net sums for all categories (using all transactions)
        grouped = self.df.groupby('categorie')['bedrag'].sum()
        
        if expense_only:
            # Filter: only keep categories where the NET sum is negative (expense)
            # This ensures refunds are accounted for (e.g. -100 + 20 = -80 net expense)
            grouped = grouped[grouped < 0]
            
        return grouped.abs().to_dict()
    
    def get_date_range(self) -> Tuple[Optional[date], Optional[date]]:
        """
        Get the date range of transactions.
        
        Returns:
            Tuple of (min_date, max_date)
        """
        if self.df.empty:
            return (None, None)
        
        return (self.df['datum'].min().date(), self.df['datum'].max().date())
    
    # NOTE: In the refactor, direct mutation filter methods like filter_by_date_range 
    # should be avoided if we want immutability, but sticking to existing pattern for now
    # while optimizing internals.
    # Actually, modifying self.df invalidates cached properties. 
    # Since we are caching, we must clear cache if we modify self.df.
    # Better approach: The UI should create a NEW Analytics instance for filtered views.
    # I will allow these methods but they will clear the cache (or I'll remove lru_cache for methods that depend on mutable state?)
    # Actually, the best way for this existing app structure is to treat Analytics as immutable locally 
    # and have the UI instantiate a fresh one for filtered data (which `views/dashboard.py` already does!)
    # So I will REMOVE the mutator methods `filter_by_date_range` and `filter_by_categories` from this class
    # and rely on the UI passing filtered lists or creating new Analytics objects. 
    # BUT, `views/dashboard.py` currently CALLS them. I need to keep them or refactor UI.
    # Refactoring UI is part of the plan. I will keep them but make sure they handle cache clearing if used.
    # OR simpler: Don't cache everything, or just accept that `dashboard.py` creates a NEW instance for filtered data anyway.
    # Checking dashboard.py:
    # 1. `analytics = Analytics(dashboard_transactions)`
    # 2. `analytics.filter_by_date_range(...)` -> This MUTATES local state.
    # 3. `analytics.filter_by_categories(...)` -> Mutates local state.
    # 
    # If I add caching, mutation becomes dangerous.
    # I will support mutation but I need to clear cache.
    
    def filter_by_date_range(self, start_date: date, end_date: date):
        """
        Filter transactions by date range in place.
        INVALIDATES CACHE.
        
        Args:
            start_date: Start date
            end_date: End date
        """
        if not self.df.empty:
            mask = (self.df['datum'].dt.date >= start_date) & (self.df['datum'].dt.date <= end_date)
            self.df = self.df[mask]
            self._clear_caches()
    
    def filter_by_categories(self, categories: List[str]):
        """
        Filter transactions by categories in place.
        INVALIDATES CACHE.
        
        Args:
            categories: List of category names to include
        """
        if not self.df.empty and categories:
            self.df = self.df[self.df['categorie'].isin(categories)]
            self._clear_caches()

    def _clear_caches(self):
        """Clear all LRU caches and cached properties."""
        # Clear cached properties
        if '_positive_transactions' in self.__dict__:
            del self.__dict__['_positive_transactions']
        if '_negative_transactions' in self.__dict__:
            del self.__dict__['_negative_transactions']
        
        # Clear LRU caches
        self.get_total_income.cache_clear()
        self.get_total_expenses.cache_clear()
        self.get_category_totals.cache_clear()
        self.get_monthly_totals.cache_clear()
        self.get_monthly_by_category.cache_clear()
        self.get_investment_percentage.cache_clear()
        self.get_year_over_year_comparison.cache_clear()
    
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
