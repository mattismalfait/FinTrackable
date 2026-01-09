"""
Bank-agnostic CSV parser with AI-powered auto-detection.
Backward compatible wrapper that uses the new parser factory system.
"""

import pandas as pd
from typing import List, Tuple
from models.transaction import Transaction
from services.parsers.parser_factory import get_parser_factory
import logging

logger = logging.getLogger(__name__)


class CSVParser:
    """
    Universal CSV parser that handles any bank's transaction format.
    Uses AI to automatically detect column mappings.
    """
    
    def __init__(self):
        """Initialize parser with factory."""
        self.factory = get_parser_factory()
        self.last_detected_bank = None
    
    def process_csv(self, uploaded_file) -> Tuple[List[Transaction], pd.DataFrame, List[str]]:
        """
        Process ANY bank's CSV file using AI-powered auto-detection.
        
        This method:
        1. Reads the uploaded file
        2. Uses AI to automatically detect column mappings (date, amount, description, etc.)
        3. Converts to standardized Transaction objects
        4. Works with ANY bank, ANY language, ANY CSV format
        
        Args:
            uploaded_file: Streamlit UploadedFile object
            
        Returns:
            Tuple of (list of Transactions, DataFrame, list of errors/warnings)
        """
        try:
            # Read file content
            uploaded_file.seek(0)
            file_content = uploaded_file.read()
            
            # Process with automatic format detection
            transactions, df, errors, detected_bank = self.factory.process_file(
                file_content=file_content,
                bank_id=None,  # Auto-detect
                filename=uploaded_file.name
            )
            
            self.last_detected_bank = detected_bank
            
            # Add info message about detection
            if detected_bank:
                bank_info = next(
                    (b for b in self.factory.get_available_banks() if b['id'] == detected_bank),
                    None
                )
                if bank_info:
                    info_msg = f"✅ Detected format: {bank_info['name']}"
                    if bank_info['id'] == 'generic_csv':
                        info_msg += " (AI auto-detection used)"
                    errors.insert(0, info_msg)
            
            return transactions, df, errors
            
        except Exception as e:
            logger.error(f"CSV processing error: {str(e)}")
            return [], pd.DataFrame(), [f"❌ Error processing file: {str(e)}"]
    
    def get_supported_formats(self) -> List[dict]:
        """
        Get list of optimized bank formats (optional - AI handles all formats).
        
        Returns:
            List of bank format information
        """
        return self.factory.get_available_banks()
    
    def get_last_detected_format(self) -> str:
        """Get the bank format that was detected in the last parse."""
        return self.last_detected_bank
    
    # Legacy compatibility methods
    def parse_csv(self, uploaded_file):
        """Legacy method - redirects to process_csv."""
        transactions, df, errors = self.process_csv(uploaded_file)
        return df, errors
    
    def df_to_transactions(self, df: pd.DataFrame):
        """Legacy method - not used in new architecture."""
        # This is handled internally by the parsers now
        return [], ["⚠️ Use process_csv() instead"]
