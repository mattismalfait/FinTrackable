"""
Excel Parser for bank transactions.
Handles .xlsx and .xls files using AI-powered column detection.
"""

import pandas as pd
import io
from typing import List, Tuple, Optional, Dict
from models.transaction import Transaction
from services.parsers.base_parser import BankParser
from services.parsers.generic_parser import AIColumnDetector
from utils.text_cleaner import clean_transaction_description
import logging

logger = logging.getLogger(__name__)


class ExcelParser(BankParser):
    """
    Universal Excel parser that handles ANY bank's Excel export.
    Uses AI to automatically detect column mappings.
    """
    
    def __init__(self, config: Dict):
        super().__init__(config)
        self.ai_detector = AIColumnDetector()
        self.detected_mapping = None
        
    def parse_csv(self, file_content: bytes) -> Tuple[Optional[pd.DataFrame], List[str]]:
        """
        Implementation of parse_csv for Excel files.
        (Named parse_csv to maintain compatibility with the base interface).
        """
        errors = []
        try:
            # Use pandas to read Excel from bytes
            # We try to read the first sheet by default
            df = pd.read_excel(io.BytesIO(file_content))
            
            # Remove empty rows and columns
            df = df.dropna(how='all').dropna(axis=1, how='all')
            
            if df.empty:
                errors.append("❌ Excel bestand is leeg")
                return None, errors
                
            # Use AI to detect columns
            sample_rows = df.head(5).to_dict('records')
            # Convert keys to strings for AI prompt
            columns = [str(c) for c in df.columns.tolist()]
            
            self.detected_mapping = self.ai_detector.detect_column_mapping(
                columns,
                sample_rows
            )
            
            has_date = 'date' in self.detected_mapping
            has_money = any(k in self.detected_mapping for k in ['amount', 'income', 'expense'])

            if not self.detected_mapping or not has_date or not has_money:
                errors.append("⚠️ AI kon de vereiste kolommen (datum en bedrag/inkomen/uitgave) niet vinden")
                
            logger.info(f"Successfully parsed Excel file. AI mapping: {self.detected_mapping}")
            return df, errors
            
        except Exception as e:
            logger.error(f"Excel parse error: {str(e)}")
            errors.append(f"❌ Fout bij het lezen van Excel bestand: {str(e)}")
            return None, errors

    def df_to_transactions(self, df: pd.DataFrame) -> Tuple[List[Transaction], List[str]]:
        """Convert Excel DataFrame to transactions using AI mapping."""
        transactions = []
        errors = []
        
        if not self.detected_mapping:
            return [], ["❌ Geen kolom-mapping gevonden voor dit bestand"]
            
        date_col = self.detected_mapping.get('date')
        amount_col = self.detected_mapping.get('amount')
        income_col = self.detected_mapping.get('income')
        expense_col = self.detected_mapping.get('expense')
        name_col = self.detected_mapping.get('counterparty_name', self.detected_mapping.get('description'))
        desc_col = self.detected_mapping.get('description')
        
        for idx, row in df.iterrows():
            try:
                # Parse date
                val_date = row.get(date_col)
                if isinstance(val_date, pd.Timestamp):
                    datum = val_date.date()
                else:
                    datum = self.parse_date(str(val_date))
                
                if not datum:
                    continue # Skip invalid dates
                
                # Parse amount
                def get_val(col_name):
                    val = row.get(col_name)
                    if pd.isna(val) or val == "":
                        return None
                    if isinstance(val, (int, float, complex)) and not isinstance(val, bool):
                        from decimal import Decimal
                        return Decimal(str(val))
                    return self.parse_amount(str(val))

                bedrag = None
                if amount_col:
                    bedrag = get_val(amount_col)
                elif income_col and expense_col:
                    from decimal import Decimal
                    inc = get_val(income_col) or Decimal(0)
                    exp = get_val(expense_col) or Decimal(0)
                    bedrag = inc - abs(exp)
                
                if bedrag is None:
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
                # Silently skip bad rows in batch
                continue
        
        return transactions, errors

    def detect_format(self, df: pd.DataFrame) -> bool:
        """Excel parser is generic."""
        return True
