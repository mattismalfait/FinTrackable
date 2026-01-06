"""
Data model for categories.
"""

from pydantic import BaseModel
from typing import List, Dict, Optional

class CategoryRule(BaseModel):
    """Rule for categorizing transactions."""
    
    field: str  # 'naam_tegenpartij', 'omschrijving', or 'bedrag'
    contains: Optional[List[str]] = None  # For text matching
    condition: Optional[str] = None  # For 'bedrag': 'positive' or 'negative'

class Category(BaseModel):
    """Category data model."""
    
    id: Optional[str] = None
    user_id: Optional[str] = None
    name: str
    rules: List[Dict] = []
    color: str = "#9ca3af"
    
    def matches(self, transaction) -> bool:
        """
        Check if a transaction matches this category's rules.
        
        Args:
            transaction: Transaction object to check
            
        Returns:
            bool: True if transaction matches any rule
        """
        if not self.rules:
            return False
        
        for rule_dict in self.rules:
            rule = CategoryRule(**rule_dict)
            
            # Check text field matching
            if rule.contains:
                field_value = ""
                if rule.field == "naam_tegenpartij":
                    field_value = transaction.naam_tegenpartij or ""
                elif rule.field == "omschrijving":
                    field_value = transaction.omschrijving or ""
                
                # Case-insensitive matching
                field_value_lower = field_value.lower()
                for keyword in rule.contains:
                    if keyword.lower() in field_value_lower:
                        return True
            
            # Check bedrag condition
            if rule.condition:
                if rule.condition == "positive" and transaction.bedrag > 0:
                    return True
                elif rule.condition == "negative" and transaction.bedrag < 0:
                    return True
        
        return False
    
    def to_dict(self) -> dict:
        """Convert category to dictionary for database insertion."""
        return {
            "name": self.name,
            "rules": self.rules,
            "color": self.color
        }
