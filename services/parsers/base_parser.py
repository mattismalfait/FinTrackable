"""
Base parser interface for bank-agnostic transaction import.
All bank-specific parsers must implement this interface.
"""

from abc import ABC, abstractmethod
from typing import List, Tuple, Dict, Optional
from datetime import date
from decimal import Decimal
import pandas as pd
from models.transaction import Transaction


class BankParser(ABC):
    """Abstract base class for bank-specific CSV parsers."""
    
    def __init__(self, config: Dict):
        """
        Initialize parser with bank-specific configuration.
        
        Args:
            config: Bank format configuration dictionary
        """
        self.config = config
        self.name = config.get('name', 'Unknown Bank')
        self.description = config.get('description', '')
    
    @abstractmethod
    def parse_csv(self, file_content: bytes) -> Tuple[Optional[pd.DataFrame], List[str]]:
        """
        Parse CSV file content into a pandas DataFrame.
        
        Args:
            file_content: Raw bytes of the CSV file
            
        Returns:
            Tuple of (DataFrame with standardized columns, list of errors)
        """
        pass
    
    @abstractmethod
    def df_to_transactions(self, df: pd.DataFrame) -> Tuple[List[Transaction], List[str]]:
        """
        Convert parsed DataFrame to list of Transaction objects.
        
        Args:
            df: Pandas DataFrame with transaction data
            
        Returns:
            Tuple of (list of Transactions, list of errors)
        """
        pass
    
    @abstractmethod
    def detect_format(self, df: pd.DataFrame) -> bool:
        """
        Detect if the DataFrame matches this bank's format.
        
        Args:
            df: Pandas DataFrame to analyze
            
        Returns:
            True if format matches, False otherwise
        """
        pass
    
    def process_file(self, file_content: bytes) -> Tuple[List[Transaction], pd.DataFrame, List[str]]:
        """
        Complete processing pipeline: parse CSV and convert to transactions.
        
        Args:
            file_content: Raw bytes of the CSV file
            
        Returns:
            Tuple of (list of Transactions, DataFrame, list of errors)
        """
        # Parse CSV
        df, parse_errors = self.parse_csv(file_content)
        
        if df is None or df.empty:
            return [], pd.DataFrame(), parse_errors
        
        # Convert to transactions
        transactions, conversion_errors = self.df_to_transactions(df)
        
        all_errors = parse_errors + conversion_errors
        
        return transactions, df, all_errors
    
    def parse_date(self, date_str: str) -> Optional[date]:
        """
        Parse date string using configured date formats and global defaults.
        """
        from datetime import datetime
        import re
        
        if pd.isna(date_str) or not date_str:
            return None
        
        date_str = str(date_str).strip()
        
        # Clean up some common artifacts
        date_str = re.sub(r'\s+', ' ', date_str)
        
        # Common date formats to try as fallback
        default_formats = [
            "%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%m/%d/%Y",
            "%d-%b-%Y", "%d %b %Y", "%d %B %Y", "%Y%m%d",
            "%Y/%m/%d", "%d.%m.%Y"
        ]
        
        # Merge configured and default formats
        configured_formats = self.config.get('date_formats', [])
        if isinstance(configured_formats, str):
            configured_formats = [configured_formats]
            
        all_formats = configured_formats + [f for f in default_formats if f not in configured_formats]
        
        for fmt in all_formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
        
        logger.warning(f"Failed to parse date string: '{date_str}'")
        return None
    
    def parse_amount(self, amount_str: str) -> Optional[Decimal]:
        """
        Parse amount string to Decimal using robust cleaning logic.
        """
        if pd.isna(amount_str) or amount_str == "":
            return None
        
        try:
            # If already numeric
            if isinstance(amount_str, (int, float, Decimal)):
                return Decimal(str(amount_str))
                
            amount_str = str(amount_str).strip()
            
            # Remove currency symbols and common text
            amount_str = amount_str.replace('€', '').replace('EUR', '').replace('$', '').replace('USD', '').strip()
            
            # Detect separators if "auto" or lists are provided
            decimal_sep = self.config.get('decimal_separator', '.')
            thousands_sep = self.config.get('thousands_separator', ',')
            
            # Robust normalization:
            # 1. If we have both , and .
            if ',' in amount_str and '.' in amount_str:
                # The one that appears last is usually the decimal separator
                if amount_str.rfind(',') > amount_str.rfind('.'):
                    amount_str = amount_str.replace('.', '').replace(',', '.')
                else:
                    amount_str = amount_str.replace(',', '')
            # 2. If we only have ,
            elif ',' in amount_str:
                # If there's only one , and it's near the end (2 digits after), it's likely decimal
                # Otherwise if there are multiple or it's not near the end, it's likely thousands
                parts = amount_str.split(',')
                if len(parts) == 2 and len(parts[1]) <= 2:
                    amount_str = amount_str.replace(',', '.')
                else:
                    amount_str = amount_str.replace(',', '')
            
            # Remove any remaining non-numeric characters except . and -
            import re
            amount_str = re.sub(r'[^\d.-]', '', amount_str)
            
            if not amount_str:
                return None
                
            return Decimal(amount_str)
        except Exception as e:
            logger.debug(f"Failed to parse amount '{amount_str}': {str(e)}")
            return None
