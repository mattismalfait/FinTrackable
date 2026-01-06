"""
Intelligent category suggestion service.
Analyzes transactions and proposes categories based on patterns.
"""

from typing import List, Dict, Tuple
from collections import defaultdict
from models.transaction import Transaction
from decimal import Decimal

class CategorySuggester:
    """Suggests categories based on transaction analysis."""
    
    # Common keywords for automatic categorization (Merged with defaults)
    CATEGORY_KEYWORDS = {
        "Eten & Drinken": [
            "delhaize", "colruyt", "carrefour", "albert heijn", "aldi", "lidl",
            "restaurant", "cafe", "bar", "pizza", "sushi", "fritkot",
            "uber eats", "deliveroo", "takeaway", "bakker", "de brug"
        ],
        "Wonen": [
            "huur", "verhuurder", "electrabel", "engie", "proximus", "telenet",
            "water", "gas", "elektriciteit", "internet", "wifi"
        ],
        "Transport": [
            "nmbs", "de lijn", "stib", "mivb", "uber", "taxi", "shell",
            "total", "benzine", "parking", "villo", "cambio"
        ],
        "Vrije Tijd": [
            "netflix", "spotify", "cinema", "kinepolis", "ugc", "steam",
            "playstation", "xbox", "concert", "festival", "museum", "theater"
        ],
        "Sport & Gezondheid": [
            "basic-fit", "fitness", "gym", "sportcity", "apotheek",
            "pharmacy", "dokter", "tandarts", "ziekenhuis"
        ],
        "Kleding": [
            "h&m", "zara", "c&a", "primark", "bershka", "mango",
            "nike", "adidas", "schoenen"
        ],
        "Reizen": [
            "booking", "airbnb", "ryanair", "brussels airlines", "thalys",
            "eurostar", "hotel", "hostel", "trip"
        ],
        "Investeren": [
            "saxo", "bolero", "degiro", "binance", "coinbase",
            "beleggen", "aandelen", "crypto"
        ],
        "Inkomen": ["idefix", "salaris", "loon", "bonus", "teruggave"]
    }
    
    COLORS = [
        "#10b981",  # Green
        "#f59e0b",  # Orange  
        "#ef4444",  # Red
        "#3b82f6",  # Blue
        "#8b5cf6",  # Purple
        "#06b6d4",  # Cyan
        "#6b7280",  # Gray
        "#ec4899",  # Pink
        "#14b8a6",  # Teal
        "#f97316",  # Dark Orange
    ]
    
    def __init__(self, threshold_count: int = 2, user_categories: List[Dict] = None):
        """
        Initialize suggester.
        
        Args:
            threshold_count: Minimum number of transactions to suggest a category
            user_categories: Custom categories from database to use as rules
        """
        self.threshold_count = threshold_count
        
        # Merge DB rules into KEYWORDS
        if user_categories:
            for cat in user_categories:
                name = cat['name']
                rules = cat.get('rules', [])
                
                # Extract 'contains' keywords from rules
                db_keywords = []
                for rule in rules:
                    if rule.get('field') in ['naam_tegenpartij', 'omschrijving'] and rule.get('contains'):
                        db_keywords.extend(rule.get('contains'))
                
                if db_keywords:
                    if name not in self.CATEGORY_KEYWORDS:
                        self.CATEGORY_KEYWORDS[name] = []
                    # Append new keywords and deduplicate
                    self.CATEGORY_KEYWORDS[name] = list(set(self.CATEGORY_KEYWORDS[name] + db_keywords))
                    
                    # Also ensure colors are synced if possible (though CATEGORY_KEYWORDS doesn't store colors)
    
    def analyze_and_suggest(self, transactions: List[Transaction]) -> Tuple[Dict[str, Dict], List[Transaction]]:
        """
        Analyze transactions and suggest categories.
        
        Args:
            transactions: List of transactions to analyze
            
        Returns:
            Tuple: (Dict of suggested categories, List of categorized transactions)
        """
        # First, enrich transaction names to avoid "Onbekend" or "---" fields
        for t in transactions:
            self._enrich_transaction_name(t)

        suggestions = {}
        processed_transactions = []
        
        # Group transactions by counterparty
        counterparty_groups = self._group_by_counterparty(transactions)
        
        # Track which transactions got which category
        txn_to_cat = {}
        
        # Analyze each group
        for counterparty, txns in counterparty_groups.items():
            # Match to category and get the specific reason (keyword)
            matched_category, reason = self._match_to_category(counterparty, txns)
            
            if matched_category:
                if matched_category not in suggestions:
                    suggestions[matched_category] = {
                        'name': matched_category,
                        'counterparties': set(),
                        'transaction_count': 0,
                        'avg_amount': Decimal('0'),
                        'color': self._get_color_for_category(matched_category),
                        'description': self._get_description(matched_category),
                        'reasons': set(),
                        'keywords': self.CATEGORY_KEYWORDS.get(matched_category, [])
                    }
                
                suggestions[matched_category]['counterparties'].add(counterparty.title())
                suggestions[matched_category]['transaction_count'] += len(txns)
                suggestions[matched_category]['avg_amount'] += sum(t.bedrag for t in txns)
                if reason:
                    suggestions[matched_category]['reasons'].add(reason)
                
                for t in txns:
                    txn_to_cat[id(t)] = matched_category
            else:
                for t in txns:
                    txn_to_cat[id(t)] = "Overig"

        # Finalize stats
        for cat_name, cat_data in suggestions.items():
            if cat_data['transaction_count'] > 0:
                cat_data['avg_amount'] = cat_data['avg_amount'] / cat_data['transaction_count']
            cat_data['counterparties'] = list(cat_data['counterparties'])
            cat_data['reasons'] = list(cat_data['reasons'])
        
        # Check for income specifically if not already caught
        income_txns = [t for t in transactions if t.bedrag > 0]
        if income_txns and 'Inkomen' not in suggestions:
            suggestions['Inkomen'] = {
                'name': 'Inkomen',
                'counterparties': list(set(t.naam_tegenpartij.title() for t in income_txns if t.naam_tegenpartij)),
                'transaction_count': len(income_txns),
                'avg_amount': sum(t.bedrag for t in income_txns) / len(income_txns),
                'color': '#3b82f6',
                'description': 'Salarissen en andere inkomsten',
                'reasons': ['Positieve bedragen (inkomst)'],
                'keywords': []
            }
            for t in income_txns:
                txn_to_cat[id(t)] = 'Inkomen'
        
        # Add "Overig" for uncategorized
        if 'Overig' not in suggestions:
            suggestions['Overig'] = {
                'name': 'Overig',
                'counterparties': [],
                'transaction_count': 0,
                'avg_amount': Decimal('0'),
                'color': '#9ca3af',
                'description': 'Niet gecategoriseerde transacties',
                'reasons': ['Standaard drempelwaarde'],
                'keywords': []
            }
        
        # Apply categories to transactions
        for t in transactions:
            category = txn_to_cat.get(id(t), "Overig")
            t.categorie = category
            processed_transactions.append(t)
        
        return suggestions, processed_transactions

    def _enrich_transaction_name(self, t: Transaction):
        """Improve transaction naming for vague counterparties."""
        original_name = (t.naam_tegenpartij or "").strip()
        description = (t.omschrijving or "").lower()
        
        # 1. Detect vague/generic names (including KBC's "---" or empty)
        vague_terms = ["", "-", "--", "---", "onbekend", "overschrijving", "betaling", "mededeling", "interne overschrijving"]
        is_vague = not original_name or original_name.lower() in vague_terms
        
        # 2. Try to find a merchant name in keywords if it's vague
        if is_vague:
            for category, keywords in self.CATEGORY_KEYWORDS.items():
                for kw in keywords:
                    if kw in description:
                        # Use the matching keyword as the new name
                        t.naam_tegenpartij = kw.title()
                        return
            
            # If still nothing but it's a positive amount, maybe it's "Inkomen"
            if t.bedrag > 0:
                t.naam_tegenpartij = "Inkomen / Teruggave"
                return
                
            # Fallback: Use a snippet of the description if available
            if t.omschrijving and len(t.omschrijving) > 5:
                # Take first 3-4 words or first 30 chars
                snippet = t.omschrijving[:30].strip()
                if len(t.omschrijving) > 30:
                    snippet += "..."
                t.naam_tegenpartij = snippet
            else:
                t.naam_tegenpartij = "Onbekend"
        
        # 3. Even if not vague, clean up common uppercase/noise
        # e.g. "DELHAIZE MERELBEKE" -> "Delhaize"
        elif not is_vague:
            name_lower = original_name.lower()
            for category, keywords in self.CATEGORY_KEYWORDS.items():
                for kw in keywords:
                    if kw in name_lower and len(kw) > 3:
                        t.naam_tegenpartij = kw.title()
                        return
            
            # If no keyword match, just title case the existing name
            t.naam_tegenpartij = original_name.title()

    def _group_by_counterparty(self, transactions: List[Transaction]) -> Dict[str, List[Transaction]]:
        """Group transactions by counterparty."""
        groups = defaultdict(list)
        
        for txn in transactions:
            if txn.naam_tegenpartij:
                normalized = txn.naam_tegenpartij.lower().strip()
                groups[normalized].append(txn)
            elif txn.omschrijving:
                # If no counterparty, maybe we can group by something in description?
                # For now just group by "Unknown" to analyze later
                groups["onbekend"].append(txn)
        
        return groups
    
    def _match_to_category(self, counterparty: str, txns: List[Transaction]) -> Tuple[str, str]:
        """Match counterparty to a predefined category. Returns (Category, Reason)."""
        counterparty_lower = counterparty.lower()
        
        # Check if it's income (positive amount)
        if all(t.bedrag > 0 for t in txns):
            return "Inkomen", "Positief bedrag"
        
        # Try to match with keywords in counterparty OR description
        for category, keywords in self.CATEGORY_KEYWORDS.items():
            for keyword in keywords:
                # Check counterparty
                if keyword in counterparty_lower:
                    return category, f"Match op '{keyword}'"
                
                # Check description of all transactions in this group
                for t in txns:
                    if t.omschrijving and keyword in t.omschrijving.lower():
                        return category, f"Omschrijving bevat '{keyword}'"
        
        return None, None
    
    def _get_color_for_category(self, category: str) -> str:
        """Get color for a category."""
        category_colors = {
            "Eten & Drinken": "#f59e0b",
            "Wonen": "#6b7280",
            "Transport": "#06b6d4",
            "Vrije Tijd": "#8b5cf6",
            "Sport & Gezondheid": "#ef4444",
            "Kleding": "#ec4899",
            "Reizen": "#14b8a6",
            "Investeren": "#10b981",
            "Inkomen": "#3b82f6",
            "Overig": "#9ca3af"
        }
        return category_colors.get(category, self.COLORS[0])
    
    def _get_description(self, category: str) -> str:
        """Get description for a category."""
        descriptions = {
            "Eten & Drinken": "Supermarkten, restaurants en voedselgerelateerde uitgaven",
            "Wonen": "Huur, utilities, internet en huishoudelijke kosten",
            "Transport": "Openbaar vervoer, taxi's, brandstof en parkeren",
            "Vrije Tijd": "Entertainment, streaming diensten en hobby's",
            "Sport & Gezondheid": "Fitness, sport en medische kosten",
            "Kleding": "Kledingwinkels en schoenen",
            "Reizen": "Vluchten, hotels en vakantiegerelateerde kosten",
            "Investeren": "Beleggingen, sparen en crypto",
            "Inkomen": "Salarissen en andere inkomsten",
            "Overig": "Niet gecategoriseerde transacties"
        }
        return descriptions.get(category, "")
