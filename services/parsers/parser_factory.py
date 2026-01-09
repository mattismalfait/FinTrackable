"""
Parser factory and manager for bank-agnostic transaction import.
Automatically selects the appropriate parser based on file content.
"""

import json
import os
from typing import List, Tuple, Optional, Dict
import pandas as pd
from services.parsers.base_parser import BankParser
from services.parsers.kbc_parser import KBCParser
from services.parsers.generic_parser import GenericBankParser
from services.parsers.excel_parser import ExcelParser
from models.transaction import Transaction
import logging

logger = logging.getLogger(__name__)


class ParserFactory:
    """Factory for creating and managing bank-specific parsers."""
    
    def __init__(self, config_path: str = None):
        """
        Initialize parser factory with bank format configurations.
        
        Args:
            config_path: Path to bank_formats.json configuration file
        """
        if config_path is None:
            # Default to config directory
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            config_path = os.path.join(base_dir, 'config', 'bank_formats.json')
        
        self.config_path = config_path
        self.parsers = {}
        self.load_configurations()
    
    def load_configurations(self):
        """Load bank format configurations from JSON file."""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                configs = json.load(f)
            
            # Create parser instances for each enabled bank
            for bank_id, config in configs.items():
                if not config.get('enabled', True):
                    continue
                
                # Map bank IDs to specific parser classes
                if bank_id.startswith('kbc'):
                    self.parsers[bank_id] = KBCParser(config)
                elif bank_id == 'generic_excel' or bank_id.endswith('_excel'):
                    self.parsers[bank_id] = ExcelParser(config)
                elif bank_id == 'generic_csv':
                    # Generic parser is the fallback
                    self.parsers[bank_id] = GenericBankParser(config)
                else:
                    # For other banks without specific parsers, use generic
                    self.parsers[bank_id] = GenericBankParser(config)
            
            logger.info(f"Loaded {len(self.parsers)} bank parsers")
            
        except FileNotFoundError:
            logger.warning(f"Config file not found: {self.config_path}")
            # Create default KBC parser
            self._create_default_kbc_parser()
        except Exception as e:
            logger.error(f"Error loading parser configs: {str(e)}")
            self._create_default_kbc_parser()
    
    def _create_default_kbc_parser(self):
        """Create default KBC parser for backward compatibility."""
        default_config = {
            "name": "KBC Bank (Default)",
            "enabled": True,
            "encoding": ["utf-8", "latin-1", "iso-8859-1", "cp1252"],
            "delimiter": ";",
            "decimal_separator": ",",
            "date_formats": ["%d/%m/%Y", "%Y-%m-%d"],
            "column_mapping": {
                "date": "Datum",
                "amount": "Bedrag",
                "counterparty_name": "Naam tegenpartij",
                "description": "Omschrijving"
            }
        }
        self.parsers['kbc_dutch'] = KBCParser(default_config)
    
    def detect_bank_format(self, file_content: bytes, filename: Optional[str] = None) -> Optional[str]:
        """
        Automatically detect which bank format the file uses.
        
        Args:
            file_content: Raw file content as bytes
            filename: Optional filename to help with extension detection
            
        Returns:
            Bank ID string or None if no match
        """
        # Extension-based pre-filtering
        is_excel = False
        if filename:
            ext = filename.lower().split('.')[-1]
            if ext in ['xlsx', 'xls', 'xlsm']:
                is_excel = True

        # Try each parser to see which one can handle the file
        for bank_id, parser in self.parsers.items():
            if bank_id in ['generic_csv', 'generic_excel']:
                continue  # Save generics as fallback
            
            # Skip CSV parsers for Excel files and vice versa
            if is_excel and not isinstance(parser, ExcelParser):
                 continue
            if not is_excel and isinstance(parser, ExcelParser):
                 continue

            try:
                df, errors = parser.parse_csv(file_content)
                if df is not None and not df.empty and parser.detect_format(df):
                    logger.info(f"Detected bank format: {bank_id}")
                    return bank_id
            except:
                continue
        
        # If no specific parser matched, try generic based on extension
        if is_excel and 'generic_excel' in self.parsers:
            logger.info("Using generic AI-powered Excel parser")
            return 'generic_excel'
            
        if not is_excel and 'generic_csv' in self.parsers:
            logger.info("Using generic AI-powered CSV parser")
            return 'generic_csv'
        
        return None
    
    def get_parser(self, bank_id: str = None, file_content: bytes = None, filename: Optional[str] = None) -> Optional[BankParser]:
        """
        Get a parser instance, either by bank ID or by auto-detection.
        """
        # If bank_id provided, use it directly
        if bank_id and bank_id in self.parsers:
            return self.parsers[bank_id]
        
        # Otherwise, try to detect
        if file_content:
            detected_id = self.detect_bank_format(file_content, filename=filename)
            if detected_id:
                return self.parsers.get(detected_id)
        
        # Fallback based on filename extension if content detection failed
        if filename:
            ext = filename.lower().split('.')[-1]
            if ext in ['xlsx', 'xls', 'xlsm'] and 'generic_excel' in self.parsers:
                 return self.parsers['generic_excel']
        
        # Absolute fallback to generic CSV
        if 'generic_csv' in self.parsers:
            return self.parsers['generic_csv']
        
        if self.parsers:
            return list(self.parsers.values())[0]
        
        return None
    
    def get_available_banks(self) -> List[Dict[str, str]]:
        """
        Get list of available bank formats.
        
        Returns:
            List of dicts with bank info
        """
        return [
            {
                'id': bank_id,
                'name': parser.name,
                'description': parser.description
            }
            for bank_id, parser in self.parsers.items()
        ]
    
    def process_file(
        self, 
        file_content: bytes, 
        bank_id: Optional[str] = None,
        filename: Optional[str] = None
    ) -> Tuple[List[Transaction], pd.DataFrame, List[str], Optional[str]]:
        """
        Process a file with automatic bank format detection.
        """
        # Get appropriate parser
        parser = self.get_parser(bank_id=bank_id, file_content=file_content, filename=filename)
        
        if not parser:
            return [], pd.DataFrame(), ["❌ Geen geschikte parser gevonden"], None
        
        # Process file
        transactions, df, errors = parser.process_file(file_content)
        
        # Determine which bank was used
        used_bank_id = bank_id if bank_id else self.detect_bank_format(file_content, filename=filename)
        
        return transactions, df, errors, used_bank_id


# Global factory instance
_factory_instance = None


def get_parser_factory() -> ParserFactory:
    """Get singleton parser factory instance."""
    global _factory_instance
    if _factory_instance is None:
        _factory_instance = ParserFactory()
    return _factory_instance
