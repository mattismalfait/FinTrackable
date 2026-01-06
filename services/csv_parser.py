"""
CSV Parser Service for KBC bank transactions.
Handles parsing, validation, and duplicate detection.
"""

import pandas as pd
import io
from typing import List, Tuple, Optional
from datetime import datetime
from decimal import Decimal
from models.transaction import Transaction
from config.settings import CSV_COLUMNS, DATE_FORMATS
import streamlit as st

class CSVParser:
    """Parse and validate KBC CSV files."""
    
    def __init__(self):
        self.expected_columns = list(CSV_COLUMNS.values())
    
    def parse_csv(self, uploaded_file) -> Tuple[Optional[pd.DataFrame], List[str]]:
        """
        Parse uploaded CSV file.
        
        Args:
            uploaded_file: Streamlit UploadedFile object
            
        Returns:
            Tuple of (DataFrame, list of errors)
        """
        errors = []
        
        try:
            # Try different encodings
            encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']
            
            df = None
            content = None
            
            for encoding in encodings:
                try:
                    uploaded_file.seek(0)
                    content = uploaded_file.read().decode(encoding)
                    
                    # Try to detect delimiter (KBC often uses semicolon)
                    # Sample first few lines to detect delimiter
                    first_lines = content.split('\n')[:5]
                    sample = '\n'.join(first_lines)
                    
                    # Count occurrences of potential delimiters
                    comma_count = sample.count(',')
                    semicolon_count = sample.count(';')
                    
                    # Choose the most common delimiter
                    delimiter = ';' if semicolon_count > comma_count else ','
                    
                    # Try to parse with detected delimiter
                    df = pd.read_csv(
                        io.StringIO(content), 
                        sep=delimiter,
                        quotechar='"',
                        encoding=encoding,
                        on_bad_lines='skip'  # Skip malformed lines
                    )
                    break
                except UnicodeDecodeError:
                    continue
                except Exception as e:
                    # If parsing fails with one delimiter, continue to next encoding
                    continue
            
            if df is None:
                errors.append("❌ Could not decode CSV file with any supported encoding or delimiter")
                return None, errors
            
            # Validate columns
            missing_columns = set(self.expected_columns) - set(df.columns)
            if missing_columns:
                errors.append(f"❌ Missing required columns: {', '.join(missing_columns)}")
                errors.append(f"ℹ️ Found columns: {', '.join(df.columns)}")
                return None, errors
            
            # Remove rows with all NaN values
            df = df.dropna(how='all')
            
            if df.empty:
                errors.append("❌ CSV file is empty")
                return None, errors
            
            return df, errors
            
        except Exception as e:
            errors.append(f"❌ Error reading CSV: {str(e)}")
            return None, errors
    
    def parse_date(self, date_str: str) -> Optional[datetime]:
        """
        Parse date string with multiple format support.
        
        Args:
            date_str: Date string
            
        Returns:
            datetime object or None if parsing fails
        """
        if pd.isna(date_str):
            return None
        
        date_str = str(date_str).strip()
        
        for fmt in DATE_FORMATS:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        return None
    
    def parse_amount(self, amount_str: str) -> Optional[Decimal]:
        """
        Parse amount string to Decimal.
        Handles various formats including comma as decimal separator.
        
        Args:
            amount_str: Amount string
            
        Returns:
            Decimal object or None if parsing fails
        """
        if pd.isna(amount_str):
            return None
        
        try:
            # Convert to string and clean
            amount_str = str(amount_str).strip()
            
            # Replace comma with dot for decimal separator
            amount_str = amount_str.replace(',', '.')
            
            # Remove any spaces or currency symbols
            amount_str = amount_str.replace(' ', '').replace('€', '').replace('EUR', '')
            
            return Decimal(amount_str)
        except Exception:
            return None
    
    def df_to_transactions(self, df: pd.DataFrame) -> Tuple[List[Transaction], List[str]]:
        """
        Convert DataFrame to list of Transaction objects.
        
        Args:
            df: Pandas DataFrame
            
        Returns:
            Tuple of (list of Transactions, list of errors)
        """
        transactions = []
        errors = []
        
        for idx, row in df.iterrows():
            try:
                # Parse date
                datum = self.parse_date(row[CSV_COLUMNS['datum']])
                if not datum:
                    errors.append(f"⚠️ Row {idx + 1}: Invalid date format")
                    continue
                
                # Parse amount
                bedrag = self.parse_amount(row[CSV_COLUMNS['bedrag']])
                if bedrag is None:
                    errors.append(f"⚠️ Row {idx + 1}: Invalid amount format")
                    continue
                
                # Get other fields
                naam_tegenpartij = str(row.get(CSV_COLUMNS['naam_tegenpartij'], '')).strip() if not pd.isna(row.get(CSV_COLUMNS['naam_tegenpartij'])) else None
                omschrijving = str(row.get(CSV_COLUMNS['omschrijving'], '')).strip() if not pd.isna(row.get(CSV_COLUMNS['omschrijving'])) else None
                
                # Create transaction
                transaction = Transaction(
                    datum=datum.date(),
                    bedrag=bedrag,
                    naam_tegenpartij=naam_tegenpartij,
                    omschrijving=omschrijving
                )
                
                # Generate hash for duplicate detection
                transaction.generate_hash()
                
                transactions.append(transaction)
                
            except Exception as e:
                errors.append(f"⚠️ Row {idx + 1}: {str(e)}")
                continue
        
        return transactions, errors
    
    def process_csv(self, uploaded_file) -> Tuple[List[Transaction], pd.DataFrame, List[str]]:
        """
        Complete CSV processing pipeline.
        
        Args:
            uploaded_file: Streamlit UploadedFile object
            
        Returns:
            Tuple of (list of Transactions, DataFrame, list of errors)
        """
        # Parse CSV
        df, parse_errors = self.parse_csv(uploaded_file)
        
        if df is None:
            return [], pd.DataFrame(), parse_errors
        
        # Convert to transactions
        transactions, conversion_errors = self.df_to_transactions(df)
        
        all_errors = parse_errors + conversion_errors
        
        return transactions, df, all_errors
