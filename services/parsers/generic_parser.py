"""
Generic bank parser with AI-powered column detection.
Uses AI to automatically identify column mappings from any bank's CSV format.
"""

import pandas as pd
import io
import json
from typing import List, Tuple, Optional, Dict
from google import genai
from models.transaction import Transaction
from services.parsers.base_parser import BankParser
from config.settings import GEMINI_API_KEY
from utils.text_cleaner import clean_transaction_description
from datetime import date, datetime
import logging

logger = logging.getLogger(__name__)


class AIColumnDetector:
    """Uses AI to detect and map CSV columns to standardized fields."""
    
    def __init__(self, api_key: str = GEMINI_API_KEY):
        self.enabled = bool(api_key)
        if self.enabled:
            self.client = genai.Client(api_key=api_key)
            self.model_name = 'gemini-flash-latest'
            
    def _prepare_sample_data(self, sample_rows: List[Dict]) -> str:
        """Serialize sample rows to JSON string, handling dates."""
        def default_serializer(obj):
            if isinstance(obj, (datetime, date)):
                return obj.isoformat()
            if hasattr(obj, 'isoformat'): # Catch pandas Timestamp
                return obj.isoformat()
            return str(obj)
            
        return json.dumps(sample_rows[:5], indent=2, default=default_serializer)
    
    def detect_column_mapping(self, columns: List[str], sample_rows: List[Dict]) -> Dict[str, str]:
        """
        Use AI to detect which columns map to which fields.
        
        Args:
            columns: List of column names from CSV
            sample_rows: Sample data rows for context
            
        Returns:
            Dictionary mapping standard field names to CSV column names
        """
        if not self.enabled:
            return {}
        
        prompt = f"""
You are an expert at analyzing bank transaction CSV files. I need you to identify which columns contain specific transaction information.

COLUMN NAMES: {', '.join(columns)}

SAMPLE DATA (first few rows):
{self._prepare_sample_data(sample_rows)}

TASK: Map these columns to standardized field names. Output ONLY valid JSON.

KEY DEFINITIONS:
- "date": The column containing transaction dates (e.g., "Date", "Datum", "Completed").
- "amount": Use this if there is a SINGLE column for money values (e.g., "Amount", "Value", "Bedrag").
- "income": Use this if money is SPLIT. This is for incoming funds (e.g., "Deposits", "Credit", "In", "Bij").
- "expense": Use this if money is SPLIT. This is for outgoing funds (e.g., "Withdrawals", "Debit", "Out", "Af").
- "description": The main text description of the transaction.
- "counterparty_name": The name of the person or company involved. (Can be same as description).

RULES:
- Use EXACT column names from the provided list.
- If money is split into two columns, you MUST identify both "income" and "expense".
- If you can only find one money column, use "amount".
- Output ONLY valid JSON. Omit keys that you cannot find.

OUTPUT FORMAT:
{{
  "date": "Exact Col Name",
  "amount": "Exact Col Name",
  "income": "Exact Col Name",
  "expense": "Exact Col Name",
  "description": "Exact Col Name",
  "counterparty_name": "Exact Col Name"
}}

RULES:
- Use EXACT column names from the CSV
- Choose "income" AND "expense" if the bank uses two separate columns for money.
- If a field cannot be identified, omit it from the output.
- Be extremely precise with spelling and capitalization of column names.

OUTPUT ONLY THE JSON, NO EXPLANATIONS:
"""
        
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            
            result_text = response.text.strip()
            
            # Clean markdown if present
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()
            
            mapping = json.loads(result_text)
            logger.info(f"AI detected column mapping: {mapping}")
            
            return mapping
            
        except Exception as e:
            logger.error(f"AI column detection failed: {str(e)}")
            return {}


class GenericBankParser(BankParser):
    """
    Generic bank parser that uses AI to detect column mappings.
    Suitable for any bank's CSV format.
    """
    
    def __init__(self, config: Dict):
        super().__init__(config)
        self.ai_detector = AIColumnDetector()
        self.detected_mapping = None
    
    def parse_csv(self, file_content: bytes) -> Tuple[Optional[pd.DataFrame], List[str]]:
        """Parse CSV with automatic encoding and delimiter detection."""
        errors = []
        
        # Try different encodings
        encodings = self.config.get('encoding', ['utf-8', 'latin-1', 'iso-8859-1'])
        
        for encoding in encodings:
            try:
                content = file_content.decode(encoding)
                
                # Auto-detect delimiter
                first_lines = content.split('\n')[:5]
                sample = '\n'.join(first_lines)
                
                delimiters = [',', ';', '\t', '|']
                delimiter_counts = {d: sample.count(d) for d in delimiters}
                delimiter = max(delimiter_counts, key=delimiter_counts.get)
                
                # Parse with detected settings
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
                
                # Use AI to detect columns
                sample_rows = df.head(5).to_dict('records')
                self.detected_mapping = self.ai_detector.detect_column_mapping(
                    df.columns.tolist(),
                    sample_rows
                )
                
                has_date = 'date' in self.detected_mapping
                has_money = any(k in self.detected_mapping for k in ['amount', 'income', 'expense'])

                if not self.detected_mapping or not has_date or not has_money:
                    errors.append("⚠️ AI kon de vereiste kolommen (datum en bedrag/inkomen/uitgave) niet vinden")
                    continue
                
                logger.info(f"Successfully parsed with encoding={encoding}, delimiter={delimiter}")
                return df, errors
                
            except UnicodeDecodeError:
                continue
            except Exception as e:
                logger.error(f"Parse error with {encoding}: {str(e)}")
                continue
        
        errors.append("❌ Could not parse CSV file")
        return None, errors
    
    def df_to_transactions(self, df: pd.DataFrame) -> Tuple[List[Transaction], List[str]]:
        """Convert DataFrame to transactions using AI-detected mapping."""
        transactions = []
        errors = []
        
        if not self.detected_mapping:
            errors.append("❌ No column mapping available")
            return [], errors
        
        date_col = self.detected_mapping.get('date')
        amount_col = self.detected_mapping.get('amount')
        income_col = self.detected_mapping.get('income')
        expense_col = self.detected_mapping.get('expense')
        name_col = self.detected_mapping.get('counterparty_name', self.detected_mapping.get('description'))
        desc_col = self.detected_mapping.get('description')
        
        for idx, row in df.iterrows():
            try:
                # Parse date
                datum = self.parse_date(row[date_col]) if date_col else None
                if not datum:
                    errors.append(f"⚠️ Row {idx + 1}: Invalid date")
                    continue
                
                # Parse amount
                bedrag = None
                if amount_col:
                    bedrag = self.parse_amount(row[amount_col])
                elif income_col and expense_col:
                    from decimal import Decimal
                    inc = self.parse_amount(row[income_col]) or Decimal(0)
                    exp = self.parse_amount(row[expense_col]) or Decimal(0)
                    # For split columns, expense is usually positive in the file, 
                    # but it represents a decrease in balance.
                    # We treat income as positive and expense as negative.
                    bedrag = inc - abs(exp)
                
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
        """Generic parser accepts any format if AI can detect columns."""
        return True  # Always returns true since it's the fallback
