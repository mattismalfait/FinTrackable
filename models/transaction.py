"""
Data model for transactions.
"""

from pydantic import BaseModel, Field
from datetime import date
from typing import Optional
from decimal import Decimal
import hashlib

class Transaction(BaseModel):
    """Transaction data model matching KBC CSV format."""
    
    id: Optional[str] = None
    user_id: Optional[str] = None
    datum: date
    bedrag: Decimal
    naam_tegenpartij: Optional[str] = None
    omschrijving: Optional[str] = None
    categorie: Optional[str] = "Overig"
    categorie_id: Optional[str] = None
    is_confirmed: bool = False
    hash: Optional[str] = None
    
    class Config:
        arbitrary_types_allowed = True
    
    def generate_hash(self) -> str:
        """
        Generate a unique hash for duplicate detection.
        Uses datum, bedrag, naam_tegenpartij, and omschrijving.
        
        Returns:
            str: MD5 hash of transaction key fields
        """
        hash_string = f"{self.datum}|{self.bedrag}|{self.naam_tegenpartij or ''}|{self.omschrijving or ''}"
        self.hash = hashlib.md5(hash_string.encode()).hexdigest()
        return self.hash
    
    def to_dict(self) -> dict:
        """Convert transaction to dictionary for database insertion."""
        return {
            "datum": self.datum.isoformat(),
            "bedrag": float(self.bedrag),
            "naam_tegenpartij": self.naam_tegenpartij,
            "omschrijving": self.omschrijving,
            "categorie_id": self.categorie_id,
            "is_confirmed": self.is_confirmed,
            "hash": self.hash or self.generate_hash()
        }
    
    def is_income(self) -> bool:
        """Check if transaction is income (positive amount)."""
        return self.bedrag > 0
    
    def is_expense(self) -> bool:
        """Check if transaction is expense (negative amount)."""
        return self.bedrag < 0
