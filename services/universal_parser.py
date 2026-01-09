"""
Zero-config Universal Parser for any bank transaction file (CSV, Excel).
No hardcoded bank formats. Uses AI to detect architecture of the file dynamically.
"""

import pandas as pd
import io
import json
import logging
import streamlit as st
from typing import List, Tuple, Optional, Dict
from decimal import Decimal
from datetime import date, datetime
from datetime import date, datetime

from models.transaction import Transaction
from utils.text_cleaner import clean_transaction_description
from utils.ai_client import AIClient

logger = logging.getLogger(__name__)

class UniversalParser:
    """
    Truly bank-agnostic parser.
    Identifies column mapping via AI for every file with zero hardcoded assumptions.
    """
    
    def __init__(self):
        self.ai = AIClient()
        
        # Internal fields we want to map to
        self.target_fields = {
            "date": "The transaction date (e.g. 12/01/2024)",
            "amount": "The transaction amount (can be positive for income, negative for expense)",
            "income": "Incoming funds column (if split from expenses)",
            "expense": "Outgoing funds column (if split from income)",
            "counterparty": "Payee, recipient, or merchant name",
            "description": "Additional notes, memo, or transaction info"
        }

    def process_file(self, uploaded_file) -> Tuple[List[Transaction], pd.DataFrame, List[str]]:
        """
        Main entry point.
        1. Detect file type (CSV vs Excel)
        2. Read data
        3. Ask AI for column mapping based on headers and sample
        4. Convert to Transaction objects
        """
        errors = []
        try:
            filename = uploaded_file.name.lower()
            file_content = uploaded_file.read()
            uploaded_file.seek(0)
            
            # 1. Read the data into a DataFrame
            df = self._read_to_df(file_content, filename)
            if df is None or df.empty:
                return [], pd.DataFrame(), ["❌ Kon het bestand niet inlezen of het bestand is leeg."]

            # 2. Extract headers and samples
            columns = df.columns.tolist()
            sample_rows = df.head(5).to_dict('records')
            
            # 3. Ask AI to map these columns to our database fields
            mapping, raw_response = self._get_ai_mapping(columns, sample_rows)
            
            # Normalize mapping and validate case-insensitively
            def find_actual_column(requested_name):
                if not requested_name: return None
                requested_clean = str(requested_name).lower().strip()
                for col in columns:
                    if str(col).lower().strip() == requested_clean:
                        return col
                return None

            validated_mapping = {}
            if mapping:
                for target, source in mapping.items():
                    actual = find_actual_column(source)
                    if actual:
                        validated_mapping[target] = actual

            has_date = 'date' in validated_mapping
            has_money = any(k in validated_mapping for k in ['amount', 'income', 'expense'])

            if not validated_mapping or not has_date or not has_money:
                missing = []
                if not has_date: missing.append("Datum (date)")
                if not has_money: missing.append("Bedrag (amount/income/expense)")
                
                col_list = ", ".join([f"'{c}'" for c in columns])
                error_msg = f"⚠️ De AI kon de vereiste kolommen niet betrouwbaar koppelen.\n\n"
                error_msg += f"**Gevonden kolommen in je bestand:** {col_list}\n\n"
                
                if validated_mapping:
                    success_part = ", ".join([f"{k} -> '{v}'" for k, v in validated_mapping.items()])
                    error_msg += f"**AI herkende wel:** {success_part}\n\n"
                
                error_msg += f"**Ontbrekende mapping voor:** {', '.join(missing)}\n\n"
                
                # Proactive suggestions based on column names if AI failed
                likely_date = find_actual_column("Date") or find_actual_column("Datum")
                likely_debit = find_actual_column("Debit") or find_actual_column("Withdrawals")
                likely_credit = find_actual_column("Credit") or find_actual_column("Deposits")
                
                if not has_date and likely_date:
                    error_msg += f"💡 *Hint: De AI miste de datum, maar we zien een kolom genaamd '{likely_date}'.*\n"
                if not has_money and (likely_debit or likely_credit):
                    error_msg += f"💡 *Hint: De AI miste de bedragen, maar we zien split kolommen ('Debit'/'Credit').*\n"

                with st.expander("🤖 Bekijk technische AI details & Raw Response", expanded=True):
                    st.write("**Gevonden mapping na validatie:**", validated_mapping)
                    st.code(f"AI Response:\n{raw_response}", language="json")
                
                return [], df, [error_msg]

            # 4. Process rows using the validated mapping
            transactions = self._df_to_transactions(df, validated_mapping)
            
            if not transactions:
                return [], df, ["⚠️ AI herkende de kolommen, maar kon er geen geldige data uit lezen (bijv. verkeerd datumformaat of lege rijen)."]

            info_msg = f"✅ AI heeft de kolommen succesvol herkend: {', '.join([f'{k}: {v}' for k, v in mapping.items() if v])}"
            return transactions, df, [info_msg]

        except Exception as e:
            logger.error(f"Universal Parser error: {str(e)}")
            return [], pd.DataFrame(), [f"❌ Fout bij verwerken: {str(e)}"]

    def _read_to_df(self, content: bytes, filename: str) -> Optional[pd.DataFrame]:
        """Detect format and read to pandas DataFrame."""
        if filename.endswith(('.xlsx', '.xls', '.xlsm')):
            return pd.read_excel(io.BytesIO(content))
        
        # For CSV, try common encodings
        for enc in ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']:
            try:
                decoded = content.decode(enc)
                # Detect delimiter
                sample = decoded[:1024]
                delimiters = [';', ',', '\t', '|']
                counts = {d: sample.count(d) for d in delimiters}
                delimiter = max(counts, key=counts.get)
                
                return pd.read_csv(io.StringIO(decoded), sep=delimiter, on_bad_lines='skip')
            except:
                continue
        return None

    def _get_ai_mapping(self, columns: List[str], sample_rows: List[Dict]) -> Tuple[Optional[Dict], str]:
        """Use AI to identify column meanings. Returns (mapping_dict, raw_response_text)."""
        if not self.ai.enabled:
            return None, "AI-client niet geïnitialiseerd (API key of HF Token mist?)"

        # Clean sample data for JSON
        def serializer(obj):
            if isinstance(obj, (datetime, date)): return obj.isoformat()
            if hasattr(obj, 'isoformat'): return obj.isoformat()
            return str(obj)

        prompt = f"""
        # ... (prompt remains same) ...
        """
        # Re-using the logic from the original file but updated for self.ai
        # I'll keep the full prompt for correctness
        prompt = f"""
You are an expert at analyzing bank transaction files. Given the following column headers and a few sample rows, identify which columns map to our database fields.

COLUMNS IN FILE:
{', '.join([f"'{c}'" for c in columns])}

SAMPLE DATA REPRESENTATION (first rows):
{json.dumps(sample_rows, indent=2, default=serializer)}

TASK: Map the file's columns to these standardized fields:
- "date": The transaction date column (e.g., "Date", "Datum", "Completed"). REQUIRED.
- "amount": The single column containing money values (e.g., "Amount", "Value", "Bedrag").
- "income": The column for incoming funds/deposits (e.g., "Credit", "Income", "Deposits", "Bij", "Cr").
- "expense": The column for outgoing funds/withdrawals (e.g., "Debit", "Expense", "Withdrawals", "Af", "Dr").
- "counterparty": The payee/merchant/recipient name.
- "description": The transaction description or notes.

RULES:
1. You MUST use the EXACT spelling and casing of the column names provided in the "COLUMNS IN FILE" list above.
2. IMPORTANT: If the file uses split columns (e.g., "Debit" and "Credit", or "Withdrawals" and "Deposits"), you MUST map both "income" and "expense".
3. Check the SAMPLE DATA to see which column contains negative/positive numbers if it's a single "amount" column.

JSON OUTPUT FORMAT:
{{
  "date": "Exact Column Name",
  "amount": "Exact Column Name or null",
  "income": "Exact Column Name or null",
  "expense": "Exact Column Name or null",
  "counterparty": "Exact Column Name or null",
  "description": "Exact Column Name or null"
}}
"""
        raw_text = ""
        try:
            raw_text = self.ai.generate_content(prompt)
            raw_text = raw_text.strip()
            
            # Robust JSON extraction
            import re
            json_match = re.search(r'\{.*\}', raw_text, re.DOTALL)
            if json_match:
                clean_text = json_match.group(0)
            else:
                clean_text = raw_text
                
            # Remove minor JSON syntax errors often made by LLMs (like trailing commas)
            clean_text = re.sub(r',\s*\}', '}', clean_text)
            
            mapping = json.loads(clean_text)
            logger.info(f"AI Mapping received: {mapping}")
            return mapping, raw_text
        except Exception as e:
            logger.error(f"AI mapping failed: {str(e)}")
            return None, raw_text or str(e)

    def _df_to_transactions(self, df: pd.DataFrame, mapping: Dict) -> List[Transaction]:
        """Apply mapping to create Transaction objects."""
        txns = []
        
        date_col = mapping.get('date')
        amount_col = mapping.get('amount')
        income_col = mapping.get('income')
        expense_col = mapping.get('expense')
        name_col = mapping.get('counterparty')
        desc_col = mapping.get('description')

        for _, row in df.iterrows():
            try:
                # 1. Parse Date
                raw_date = row.get(date_col)
                datum = self._parse_date(raw_date)
                if not datum: continue

                # 2. Parse Amount
                bedrag = self._parse_money(row, amount_col, income_col, expense_col)
                if bedrag is None: continue

                # 3. Parse Text
                name = str(row.get(name_col, '')) if name_col and not pd.isna(row.get(name_col)) else None
                desc = str(row.get(desc_col, '')) if desc_col and not pd.isna(row.get(desc_col)) else None
                
                if desc:
                    desc = clean_transaction_description(desc)

                txn = Transaction(
                    datum=datum,
                    bedrag=bedrag,
                    naam_tegenpartij=name,
                    omschrijving=desc
                )
                txn.generate_hash()
                txns.append(txn)
            except:
                continue
        return txns

    def _parse_date(self, val) -> Optional[date]:
        if pd.isna(val): return None
        if isinstance(val, (datetime, date)): 
            return val.date() if isinstance(val, datetime) else val
        if hasattr(val, 'date'): return val.date() # Pandas Timestamp
        
        # Try string parsing
        date_str = str(val).strip()
        fmts = ["%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%m/%d/%Y", "%d-%b-%Y", "%d %b %Y", "%d.%m.%Y"]
        for fmt in fmts:
            try:
                return datetime.strptime(date_str, fmt).date()
            except:
                continue
        return None

    def _parse_money(self, row, amount_col, income_col, expense_col) -> Optional[Decimal]:
        def clean(v):
            if pd.isna(v) or v == "": return Decimal(0)
            if isinstance(v, (int, float, Decimal)): return Decimal(str(v))
            s = str(v).replace('€', '').replace('EUR', '').replace('$', '').replace(' ', '')
            # Handle , as decimal
            if ',' in s and '.' not in s: s = s.replace(',', '.')
            elif ',' in s and '.' in s:
                if s.rfind(',') > s.rfind('.'): s = s.replace('.', '').replace(',', '.')
                else: s = s.replace(',', '')
            import re
            s = re.sub(r'[^\d.-]', '', s)
            return Decimal(s) if s else Decimal(0)

        if amount_col and not pd.isna(row.get(amount_col)):
            return clean(row.get(amount_col))
        
        if income_col or expense_col:
            inc = clean(row.get(income_col)) if income_col else Decimal(0)
            exp = clean(row.get(expense_col)) if expense_col else Decimal(0)
            return inc - abs(exp)
            
        return None
