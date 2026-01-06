"""
Categorization Engine for automatic transaction categorization.
Includes rule-based matching and learning system.
"""

from typing import List, Dict, Optional
from models.transaction import Transaction
from models.category import Category
from config.settings import DEFAULT_CATEGORIES
import streamlit as st

class CategorizationEngine:
    """Intelligent categorization system with learning capabilities."""
    
    def __init__(self, user_categories: List[Dict] = None):
        """
        Initialize categorization engine.
        
        Args:
            user_categories: List of user's custom categories from database
        """
        self.categories = []
        
        # Load default categories
        for name, config in DEFAULT_CATEGORIES.items():
            category = Category(
                name=name,
                rules=config['rules'],
                color=config['color']
            )
            self.categories.append(category)
        
        # Load user-defined categories (override defaults)
        if user_categories:
            self._merge_user_categories(user_categories)
    
    def _merge_user_categories(self, user_categories: List[Dict]):
        """
        Merge user categories with defaults.
        User categories override defaults if names match.
        
        Args:
            user_categories: List of category dictionaries from database
        """
        for user_cat_dict in user_categories:
            user_cat = Category(**user_cat_dict)
            
            # Check if category exists in defaults
            existing_idx = None
            for idx, cat in enumerate(self.categories):
                if cat.name == user_cat.name:
                    existing_idx = idx
                    break
            
            if existing_idx is not None:
                # Replace default with user version
                self.categories[existing_idx] = user_cat
            else:
                # Add new custom category
                self.categories.append(user_cat)
    
    def categorize_transaction(self, transaction: Transaction) -> str:
        """
        Categorize a single transaction using defined rules.
        
        Args:
            transaction: Transaction to categorize
            
        Returns:
            str: Category name
        """
        # Try each category's rules
        for category in self.categories:
            if category.matches(transaction):
                return category.name
        
        # Default to "Overig" if no match
        return "Overig"
    
    def categorize_batch(self, transactions: List[Transaction]) -> List[Transaction]:
        """
        Categorize multiple transactions.
        
        Args:
            transactions: List of transactions to categorize
            
        Returns:
            List of transactions with categories assigned
        """
        for transaction in transactions:
            if not transaction.categorie or transaction.categorie == "Overig":
                transaction.categorie = self.categorize_transaction(transaction)
        
        return transactions
    
    def get_uncategorized(self, transactions: List[Transaction]) -> List[Transaction]:
        """
        Get transactions that are uncategorized or marked as "Overig".
        
        Args:
            transactions: List of all transactions
            
        Returns:
            List of uncategorized transactions
        """
        return [t for t in transactions if not t.categorie or t.categorie == "Overig"]
    
    def suggest_category(self, transaction: Transaction, confidence_threshold: float = 0.7) -> Optional[tuple]:
        """
        Suggest a category with confidence score.
        
        Args:
            transaction: Transaction to categorize
            confidence_threshold: Minimum confidence to return suggestion
            
        Returns:
            Tuple of (category_name, confidence) or None
        """
        # Simple confidence: 1.0 if exact match, 0.5 for partial match
        for category in self.categories:
            if category.matches(transaction):
                return (category.name, 1.0)
        
        # Could implement fuzzy matching here for partial matches
        return None
    
    def learn_from_correction(self, transaction: Transaction, correct_category: str) -> Dict:
        """
        Learn from user correction by adding a new rule.
        
        Args:
            transaction: The transaction that was corrected
            correct_category: The correct category assigned by user
            
        Returns:
            Dict with the new rule to be saved
        """
        # Create a new rule based on the most specific identifier
        new_rule = None
        
        if transaction.naam_tegenpartij:
            # Prefer tegenpartij as it's more specific
            new_rule = {
                "field": "naam_tegenpartij",
                "contains": [transaction.naam_tegenpartij]
            }
        elif transaction.omschrijving:
            # Extract key words from omschrijving (first 3 words or most specific term)
            words = transaction.omschrijving.split()[:3]
            new_rule = {
                "field": "omschrijving",
                "contains": words
            }
        
        return {
            "category": correct_category,
            "rule": new_rule
        }
    
    def get_category_colors(self) -> Dict[str, str]:
        """
        Get mapping of category names to colors.
        
        Returns:
            Dict of category_name: color
        """
        return {cat.name: cat.color for cat in self.categories}
    
    def get_category_names(self) -> List[str]:
        """
        Get list of all category names.
        
        Returns:
            List of category names
        """
        return [cat.name for cat in self.categories]
