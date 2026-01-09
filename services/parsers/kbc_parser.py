"""
KBC Bank parser - maintains backward compatibility with existing KBC CSV format.
"""

import pandas as pd
import io
from typing import List, Tuple, Optional
from models.transaction import Transaction
from services.parsers.base_parser import BankParser
from utils.text_cleaner import clean_transaction_description
import logging

logger = logging.getLogger(__name__)


class KBCParser(BankParser):
    """Parser for KBC bank CSV files in Dutch format."""
    
    def parse_csv(self, file_content: bytes) -> Tuple[Optional[pd.DataFrame], List[str]]:
        """Parse KBC-formatted CSV file."""
        errors = []
        
        # Try configured encodings
        encodings = self.config.get('encoding', ['utf-8'])
        delimiter = self.config.get('delimiter', ';')
        
        for encoding in encodings:
            try:
                content = file_content.decode(encoding)
                
                # Parse with KBC settings
                df = pd.read_csv(
                    io.StringIO(content),
                    sep=delimiter,
                    encoding=encoding,
                    on_bad_lines='skip'
                )
                
                # Remove empty rows
                df = df.dropna(how='all')
                
                if df.empty:
                    continue
                
                # Validate columns
                column_mapping = self.config.get('column_mapping', {})
                required = [column_mapping.get('date'), column_mapping.get('amount')]
                
                missing = [col for col in required if col and col not in df.columns]
                if missing:
                    errors.append(f"❌ Missing columns: {', '.join(missing)}")
                    errors.append(f"ℹ️ Found: {', '.join(df.columns)}")
                    continue
                
                logger.info(f"Successfully parsed KBC CSV with {encoding}")
                return df, errors
                
            except UnicodeDecodeError:
                continue
            except Exception as e:
                logger.error(f"KBC parse error: {str(e)}")
                continue
        
        errors.append("❌ Could not parse KBC CSV")
        return None, errors
    
    def df_to_transactions(self, df: pd.DataFrame) -> Tuple[List[Transaction], List[str]]:
        """Convert KBC DataFrame to transactions."""
        transactions = []
        errors = []
        
        column_mapping = self.config.get('column_mapping', {})
        date_col = column_mapping.get('date')
        amount_col = column_mapping.get('amount')
        name_col = column_mapping.get('counterparty_name')
        desc_col = column_mapping.get('description')
        
        for idx, row in df.iterrows():
            try:
                # Parse date
                datum = self.parse_date(row[date_col])
                if not datum:
                    errors.append(f"⚠️ Row {idx + 1}: Invalid date")
                    continue
                
                # Parse amount
                bedrag = self.parse_amount(row[amount_col])
                if bedrag is None:
                    errors.append(f"⚠️ Row {idx + 1}: Invalid amount")
                    continue
                
                # Get text fields
                naam_tegenpartij = str(row.get(name_col, '')) if name_col and not pd.isna(row.get(name_col)) else None
                omschrijving = str(row.get(desc_col, '')) if desc_col and not pd.isna(row.get(desc_col)) else None
                
                if omschrijving:
                    omschrijving = clean_transaction_description(omschrijving)
                
                # Create transaction
                transaction = Transaction(
                    datum=datum,
                    bedrag=bedrag,
                    naam_tegenpartij=naam_tegenpartij,
                    omschrijving=omschrijving
                )
                transaction.generate_hash()
                transactions.append(transaction)
                
            except Exception as e:
                errors.append(f"⚠️ Row {idx + 1}: {str(e)}")
                continue
        
        return transactions, errors
    
    def detect_format(self, df: pd.DataFrame) -> bool:
        """Detect if DataFrame matches KBC format."""
        column_mapping = self.config.get('column_mapping', {})
        required_cols = [
            column_mapping.get('date'),
            column_mapping.get('amount')
        ]
        
        return all(col in df.columns for col in required_cols if col)
