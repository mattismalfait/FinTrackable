"""
Text cleaning utilities for transaction descriptions.
"""

import re

def clean_transaction_description(description: str) -> str:
    """
    Clean transaction description by removing redundant payment method prefixes.
    
    Args:
        description: Raw transaction description
        
    Returns:
        Cleaned description with payment method text removed
    """
    if not description:
        return description
    
    # List of patterns to remove (case-insensitive)
    patterns_to_remove = [
        r'^Betaling via bancontact\s*-?\s*',
        r'^Betaling via debit mastercard\s*-?\s*',
        r'^Betaling via Bancontact\s*-?\s*',
        r'^Betaling via Debit Mastercard\s*-?\s*',
        r'^Overschrijving naar\s*-?\s*',
        r'^Overschrijving van\s*-?\s*',
        r'^Domiciliëring\s*-?\s*',
        r'^Europese overschrijving\s*-?\s*',
        r'^SEPA domiciliëring\s*-?\s*',
        r'^SEPA overschrijving\s*-?\s*',
        r'^Terugbetaling\s*-?\s*',
        r'^Storting\s*-?\s*',
        r'^Opname\s*-?\s*',
    ]
    
    cleaned = description.strip()
    
    # Apply each pattern
    for pattern in patterns_to_remove:
        cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
    
    # Remove extra whitespace
    cleaned = ' '.join(cleaned.split())
    
    return cleaned.strip()
