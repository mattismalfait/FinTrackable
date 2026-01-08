"""
AI Categorization service using Gemini to analyze and categorize transactions.
"""
import json
import logging
from typing import List, Dict, Optional
import streamlit as st
from google import genai
from models.transaction import Transaction
from config.settings import GEMINI_API_KEY, DEFAULT_CATEGORIES

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AiCategorizer:
    """AI agent for intelligent transaction analysis and categorization."""
    
    def __init__(self, api_key: str = GEMINI_API_KEY):
        """Initialize the AI categorizer with Gemini API key."""
        if not api_key:
            logger.warning("Gemini API key not found. AI features will be disabled.")
            self.enabled = False
            return
            
        self.client = genai.Client(api_key=api_key)
        self.model_name = 'gemini-1.5-flash'
        self.enabled = True


        
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
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt
                )
                results = self._parse_response(response.text)
                
                if not results:
                    st.error("⚠️ De AI heeft geen resultaten teruggegeven voor dit blok.")
                    continue

                
                # Prepare case-insensitive lookup
                cat_map = {c.lower(): c for c in getattr(self, 'available_categories', [])}

                # Map results back to transactions
                for txn, result in zip(chunk, results):
                    txn.ai_name = result.get('name', txn.naam_tegenpartij)
                    txn.ai_reasoning = result.get('reasoning', '')
                    txn.ai_confidence = float(result.get('confidence', 0.5))
                    
                    # Only change category if confidence > 0.5
                    ai_cat = result.get('category')
                    if ai_cat:
                        # 1. Exact case-insensitive mapping
                        matched_cat = cat_map.get(ai_cat.lower())
                        
                        # 2. Heuristic mapping (if AI returned "Eten" for "Eten & Drinken")
                        if not matched_cat:
                            ai_cat_lower = ai_cat.lower()
                            for db_cat in getattr(self, 'available_categories', []):
                                if ai_cat_lower in db_cat.lower() or db_cat.lower() in ai_cat_lower:
                                    matched_cat = db_cat
                                    break
                                    
                        if matched_cat and txn.ai_confidence > 0.5:
                            txn.categorie = matched_cat
                        elif not matched_cat:
                            logger.warning(f"AI suggested unknown category: {ai_cat}")
                    
                    # Update the display name if AI is confident and current name is vague
                    vague_names = ["kbc ---", "---", "", "onbekend", "overschrijving"]

                    if txn.ai_confidence > 0.8 and (not txn.naam_tegenpartij or txn.naam_tegenpartij.lower() in vague_names):
                        txn.naam_tegenpartij = txn.ai_name
                        
            except Exception as e:
                msg = f"Error calling Gemini: {str(e)}"
                logger.error(msg)
                st.error(msg) # Show to user since this is a fragment/UI context usually
                
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
As an expert financial analyst for the Belgian and European market, analyze these bank transactions.
Your goal is to enrich each transaction with accurate identifying data and the most appropriate category.

# CATEGORIES & CONTEXT:
{self.categories_context}

# YOUR TASKS:
1. IDENTIFY MERCHANT: Look at 'raw_name' and 'description'. If 'raw_name' is generic (e.g. 'KBC ---', 'Overschrijving'), extract the real merchant from the 'description' (e.g. 'STARBUCKS', 'AMAZON', 'TELENET').
2. CATEGORIZE: Pick the BEST category from the list above. Use your general knowledge for well-known brands.
3. REASONING: Briefly explain your choice (max 10 words).
4. CONFIDENCE: Score from 0.0 to 1.0 based on how sure you are.

- EXACT CATEGORY NAMES: You MUST use the exact names from the list above. No variations.
- BE DECISIVE: Avoid 'Overig' if ANY other category fits reasonably well. Use your general knowledge for merchants.
- USER SPECIFIC RULES:
    * Any transaction with the name 'MATTIS' and a large amount (e.g., > €100) is almost certainly 'Investeren'.
    * Positive amounts are generally 'Inkomen'.
- DESCRIPTION TRUMPS NAME: Bank descriptions often contain the actual merchant (like 'Albert Heijn' or 'Amazon').
- LANGUAGE: The category names are in Dutch. The transactions may be Dutch, French, or English. Use your expert context.

# OUTPUT FORMAT:
Output ONLY a valid JSON array of objects.
[{{"index": 0, "name": "Exact Merchant Name", "category": "Exact Category Name", "reasoning": "Reason here", "confidence": 0.95}}]

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
            msg = f"Failed to parse AI response: {str(e)}"
            logger.error(f"{msg} | Text: {text[:200]}...")
            # Include a snippet of the response to help the user identify the problem
            snippet = text[:100].replace("{", "{{").replace("}", "}}")
            st.error(f"⚠️ AI Parsing Fout: De AI gaf een ongeldig antwoord terug. Ontvangen snippet: '{snippet}...'")
            return []
