"""
AI Categorization service using Gemini to analyze and categorize transactions.
"""
import json
import logging
from typing import List, Dict, Optional
import streamlit as st
from models.transaction import Transaction
from config.settings import DEFAULT_CATEGORIES
from utils.ai_client import AIClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
import re

def _is_bad_name(name: str) -> bool:
    """Check if a name is likely 'gibberish' (dates, numbers, codes)."""
    if not name or len(name.strip()) < 3:
        return True
    
    # Check for direct date formats like DD/MM/YYYY or similar
    if re.search(r'\d{2}[-/]\d{2}', name):
        return True
        
    digit_count = sum(c.isdigit() for c in name)
    if digit_count > len(name) * 0.5:
        return True
        
    vague = ["kbc", "overschrijving", "betaling", "europese overschrijving", "onbekend", "diverse"]
    if name.lower().strip() in vague:
        return True
        
    return False

class AiCategorizer:
    """AI agent for intelligent transaction analysis and categorization."""
    
    def __init__(self):
        """Initialize the AI categorizer using unified AIClient."""
        self.ai = AIClient()
        self.enabled = self.ai.enabled
            
        if not self.enabled:
            return

        # Prepare category context
        self.categories_context = self._prepare_categories_context()


        
        # Prepare category context
        self.categories_context = self._prepare_categories_context()


    def set_categories(self, categories: List[Dict]):
        """Update the category context with dynamic categories from the database."""
        self.available_categories = [c.get('name') for c in categories]
        context = "Available categories and their typical matches:\n"
        for cat in categories:
            name = cat.get('name')
            rules = cat.get('rules', [])
            keywords = []
            for r in rules:
                if 'contains' in r:
                    keywords.extend(r['contains'])
            context += f"- {name}: {', '.join(keywords)}\n"
        self.categories_context = context

    def _prepare_categories_context(self) -> str:
        """Prepare a string description of categories for the prompt."""
        return self.set_categories([{'name': name, 'rules': config.get('rules', [])} 
                                   for name, config in DEFAULT_CATEGORIES.items()]) or self.categories_context


    def analyze_batch(self, transactions: List[Transaction]) -> List[Transaction]:
        """Process a batch of transactions using AI."""
        if not self.enabled or not transactions:
            return transactions

        # Prepare transactions for prompt (limit to avoid token overflow, though 1.5 is large)
        # We group them to reduce API calls
        # Increase batch size to 100 to minimize API requests
        batch_size = 100
        processed_txns = []
        
        for i in range(0, len(transactions), batch_size):
            chunk = transactions[i:i + batch_size]
            prompt = self._build_prompt(chunk)
            
            try:
                content = self.ai.generate_content(prompt)
                results = self._parse_response(content)
                
                if not results:
                    st.warning("⚠️ De AI kon deze groep transacties niet automatisch categoriseren. Je kunt ze nu handmatig toewijzen.")
                    # Fallback: keep processing without continue to ensure data isn't lost
                    results = [] 
                
                # Prepare case-insensitive lookup
                cat_map = {c.lower(): c for c in getattr(self, 'available_categories', [])}

                # Map results back to transactions
                # If AI returned fewer results than transactions, zip will truncate (safe as we just miss enrichment)
                for txn, result in zip(chunk, results):
                    txn.ai_name = result.get('name', txn.naam_tegenpartij)
                    txn.ai_reasoning = result.get('reasoning', '')
                    txn.ai_confidence = float(result.get('confidence', 0.5))
                    ai_cat = result.get('category')
                    
                    # Store raw AI suggestion
                    txn.ai_category = ai_cat
                    
                    if ai_cat:
                        # 1. Exact case-insensitive mapping
                        matched_cat = cat_map.get(ai_cat.lower())
                        
                        # 2. Heuristic mapping
                        if not matched_cat:
                            ai_cat_lower = ai_cat.lower()
                            for db_cat in getattr(self, 'available_categories', []):
                                if ai_cat_lower in db_cat.lower() or db_cat.lower() in ai_cat_lower:
                                    matched_cat = db_cat
                                    break
                                    
                        if matched_cat and txn.ai_confidence > 0.5:
                            # Limit "Overig": Do not overwrite a specific category with "Overig"
                            is_new_overig = matched_cat.lower() == 'overig'
                            has_existing_cat = txn.categorie and txn.categorie.lower() != 'overig'
                            
                            if is_new_overig and has_existing_cat:
                                logger.info(f"AI suggested Overig but kept {txn.categorie}")
                            else:
                                txn.categorie = matched_cat
                        elif not matched_cat and txn.ai_confidence > 0.5:
                            # New category suggested!
                            logger.info(f"AI suggested NEW category: {ai_cat}")
                    
                    
                    # Update the display name if AI is confident and current name is vague or looks like raw data
                    if txn.ai_confidence > 0.7:
                        current_is_bad = _is_bad_name(txn.naam_tegenpartij)
                        new_is_valid =  txn.ai_name and len(txn.ai_name.strip()) > 2
                        
                        if current_is_bad and new_is_valid:
                            logger.info(f"Overwriting bad name '{txn.naam_tegenpartij}' with '{txn.ai_name}'")
                            txn.naam_tegenpartij = txn.ai_name
                        elif not txn.naam_tegenpartij or txn.naam_tegenpartij.lower() in ["kbc ---", "---", "", "onbekend"]:
                            txn.naam_tegenpartij = txn.ai_name
                        
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Error calling Gemini: {error_msg}")
                
                if "429" in error_msg:
                    st.error("⏳ De AI-service is momenteel druk of u heeft uw limiet bereikt. Probeer het later opnieuw.")
                elif "401" in error_msg or "API key" in error_msg:
                    st.error("🔑 Er is een probleem met de API-sleutel. Controleer uw configuratie.")
                else:
                    st.error("❌ Er is een onverwachte fout opgetreden bij de AI-verwerking. Probeer het opnieuw.")
                
            processed_txns.extend(chunk)
            
        return processed_txns

    def _build_prompt(self, transactions: List[Transaction]) -> str:
        """Create the prompt for Gemini."""
        tx_data = []
        for i, t in enumerate(transactions):
            tx_data.append({
                "index": i,
                "raw_name": t.naam_tegenpartij,
                "description": t.omschrijving,
                "amount": float(t.bedrag),
                "date": t.datum.isoformat()
            })

        tx_list_str = json.dumps(tx_data, indent=2)
        
        prompt = f"""
As an international financial analysis agent, analyze these bank transactions from any bank and in any language (Dutch, French, English, German, etc.).
Your goal is to extract standardized merchant names and high-quality categories.

# CATEGORIES & CONTEXT:
{self.categories_context}

# YOUR TASKS:
1. IDENTIFY MERCHANT: Regardless of the original language (e.g., 'Betaling', 'Payment', 'Paiement'), extract the real merchant/recipient name. 
   - Remove generic banking terms (like "KBC", "ING", "European Transfer").
   - Clean up raw data strings into readable merchant names (e.g., 'ALDI 123 STORE' -> 'Aldi').
2. CATEGORIZE: Map the transaction to the BEST matching category from the list above.
   - If the merchant is international (e.g., Amazon, Shell, McDonald's), use your global knowledge to categorize them.
3. REASONING: Explain your logic in English (max 10 words).
4. CONFIDENCE: Score from 0.0 to 1.0.

# CRITICAL RULES:
- **INVESTMENT VS SAVINGS**: Do NOT categorize transfers to a 'Spaarboek' or 'Sparen' (Savings account) as 'Investeren'. Only use 'Investeren' for stocks, bonds, crypto, or institutional investment platforms (like Saxo, Bolero).
- **OVERWRITE**: If your confidence is > 50%, you MUST provide an assignment.

# OUTPUT FORMAT:
Output ONLY a valid JSON array of objects.
[{{"index": 0, "name": "Standardized Merchant", "category": "Category Name", "reasoning": "English reasoning", "confidence": 0.95}}]

# TRANSACTIONS TO ANALYZE:
{tx_list_str}
"""
        return prompt

    def _parse_response(self, text: str) -> List[Dict]:
        """Parse the JSON response from Gemini."""
        try:
            # First attempt: standard cleaning
            clean_text = text.strip()
            
            # Remove markdown delimiters
            if "```json" in clean_text:
                clean_text = clean_text.split("```json")[1].split("```")[0].strip()
            elif "```" in clean_text:
                clean_text = clean_text.split("```")[1].split("```")[0].strip()
            
            try:
                return json.loads(clean_text)
            except json.JSONDecodeError:
                # Second attempt: Regex to find the first array
                import re
                match = re.search(r'\[.*\]', clean_text, re.DOTALL)
                if match:
                    return json.loads(match.group())
                raise
                
        except Exception as e:
            logger.error(f"Failed to parse AI response: {str(e)} | Text: {text[:200]}...")
            st.warning("⚠️ De AI gaf een antwoord dat niet verwerkt kon worden. Probeer de analyse opnieuw.")
            return []
