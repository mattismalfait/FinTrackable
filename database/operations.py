"""
Database operations for transactions, categories, and user preferences.
"""

from typing import List, Optional, Dict, Set, Tuple, Union, Any
from datetime import date, datetime
from database.connection import get_supabase_client
from models.transaction import Transaction
from models.category import Category

class DatabaseOperations:
    """Handle all database CRUD operations."""
    
    def __init__(self):
        self.client = get_supabase_client()
    
    # ========================================================================
    # TRANSACTION OPERATIONS
    # ========================================================================
    
    def get_existing_hashes(self, user_id: str) -> Set[str]:
        """
        Get set of all existing transaction hashes for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            Set of hash strings
        """
        if not self.client:
            return set()
            
        try:
            # Fetch all hashes for this user
            response = self.client.table("transactions").select("hash").eq("user_id", user_id).limit(10000).execute()
            return {item['hash'] for item in response.data if item.get('hash')}
        except Exception as e:
            print(f"Error checking duplicates: {str(e)}")
            return set()

    def insert_transactions(self, transactions: List[Transaction], user_id: str) -> Dict[str, Any]:
        """
        Insert multiple transactions into the database.
        Skips duplicates based on hash.
        
        Args:
            transactions: List of Transaction objects
            user_id: User ID for ownership
            
        Returns:
            Dict with success count, skipped count, and errors
        """
        if not self.client:
            return {"success": 0, "skipped": 0, "errors": ["No database connection"]}
        
        # Ideally, we should use get_existing_hashes before calling this for bulk filtering,
        # but this method handles individual insertion safely.
        
        success_count = 0
        skipped_count = 0
        errors = []
        
        for transaction in transactions:
            try:
                # Generate hash if not present
                if not transaction.hash:
                    transaction.generate_hash()
                
                # Prepare data
                data = transaction.to_dict()
                data["user_id"] = user_id
                
                # Try to insert
                self.client.table("transactions").insert(data).execute()
                success_count += 1
                
            except Exception as e:
                error_msg = str(e)
                # Check if it's a duplicate hash error
                if "duplicate" in error_msg.lower() or "unique" in error_msg.lower():
                    skipped_count += 1
                else:
                    errors.append(f"Transaction {transaction.datum}: {error_msg}")
        
        return {
            "success": success_count,
            "skipped": skipped_count,
            "errors": errors
        }
    
    def get_transactions(self, user_id: str, start_date: Optional[date] = None, 
                        end_date: Optional[date] = None, 
                        category: Optional[str] = None,
                        is_confirmed: Optional[bool] = None) -> List[Dict]:
        """
        Retrieve transactions for a user with optional filters.
        
        Args:
            user_id: User ID
            start_date: Optional start date filter
            end_date: Optional end date filter
            category: Optional category filter
            is_confirmed: Optional confirmation status filter
            
        Returns:
            List of transaction dictionaries
        """
        if not self.client:
            return []
        
        try:
            # Join with categories to get name and color
            query = self.client.table("transactions").select("*, categories(name, color)").eq("user_id", user_id)
            
            if start_date:
                query = query.gte("datum", start_date.isoformat())
            if end_date:
                query = query.lte("datum", end_date.isoformat())
            if category:
                if len(category) > 30 and "-" in category: # Simple UUID check
                    query = query.eq("categorie_id", category)
                else:
                    query = query.eq("categories.name", category)
                    
            if is_confirmed is not None:
                query = query.eq("is_confirmed", is_confirmed)
            
            # Order by date descending
            query = query.order("datum", desc=True).limit(5000)
            
            response = query.execute()

            # Flatten the response for easier use
            processed_data = []
            for item in response.data:
                category_info = item.get('categories')
                # Handle both None and empty dict/list cases
                if category_info:
                    # If it's a list (sometimes happens with 1:many joins, though here it's 1:1), take first
                    if isinstance(category_info, list) and len(category_info) > 0:
                        cat_data = category_info[0]
                    elif isinstance(category_info, dict):
                        cat_data = category_info
                    else:
                        cat_data = {}
                    
                    item['categorie'] = str(cat_data.get('name', 'Overig')).strip()
                    item['color'] = cat_data.get('color', '#9ca3af')
                else:
                    item['categorie'] = 'Overig'
                    item['color'] = '#9ca3af'
                    
                processed_data.append(item)
                
            return processed_data
        except Exception as e:
            print(f"Error fetching transactions: {str(e)}")
            return []
    
    def confirm_transaction(self, transaction_id: str, user_id: str) -> bool:
        """Mark a transaction as confirmed."""
        if not self.client:
            return False
        try:
            self.client.table("transactions").update(
                {"is_confirmed": True}
            ).eq("id", transaction_id).eq("user_id", user_id).execute()
            return True
        except Exception as e:
            print(f"Error confirming transaction: {str(e)}")
            return False

    def update_transaction(self, transaction_id: str, updates: Dict, user_id: str) -> bool:
        """
        Update transaction fields.
        
        Args:
            transaction_id: Transaction ID
            updates: Dictionary of fields to update
            user_id: User ID
            
        Returns:
            bool: True if successful
        """
        if not self.client:
            return False
        
        try:
            self.client.table("transactions").update(updates).eq("id", transaction_id).eq("user_id", user_id).execute()
            return True
        except Exception as e:
            print(f"Error updating transaction: {str(e)}")
            return False
    
    def delete_transaction(self, transaction_id: str, user_id: str) -> bool:
        """
        Delete a transaction from the database.
        
        Args:
            transaction_id: Transaction ID to delete
            user_id: User ID for authorization
            
        Returns:
            True if successful, False otherwise
        """
        if not self.client:
            return False
            
        try:
            self.client.table("transactions").delete().eq("id", transaction_id).eq("user_id", user_id).execute()
            return True
        except Exception as e:
            print(f"Error deleting transaction: {str(e)}")
            return False

    def update_transaction_category(self, transaction_id: str, category_id: str, user_id: str, 
                                    is_confirmed: bool = False, is_lopende_rekening: bool = False, 
                                    transaction_data: Dict = {}) -> bool:
        """
        Update the category ID of a transaction.
        
        Args:
            transaction_id: Transaction ID
            category_id: New category ID
            user_id: User ID for verification
            is_confirmed: Whether the transaction is confirmed
            is_lopende_rekening: Whether the transaction is a current account transaction
            transaction_data: Dictionary containing additional transaction data like AI metadata
            
        Returns:
            bool: True if successful
        """
        if not self.client:
            return False
        
        try:
            # Update is_confirmed, is_lopende_rekening, and AI metadata
            update_data = {
                "categorie_id": category_id,
                "is_confirmed": is_confirmed,
                "is_lopende_rekening": is_lopende_rekening,
                "updated_at": datetime.now().isoformat()
            }
            
            # Optionally update AI metadata if provided
            if "ai_name" in transaction_data: update_data["ai_name"] = transaction_data["ai_name"]
            if "ai_reasoning" in transaction_data: update_data["ai_reasoning"] = transaction_data["ai_reasoning"]
            if "ai_confidence" in transaction_data: update_data["ai_confidence"] = transaction_data["ai_confidence"]
            if "naam_tegenpartij" in transaction_data: update_data["naam_tegenpartij"] = transaction_data["naam_tegenpartij"]

            response = self.client.table("transactions").update(update_data).eq("id", transaction_id).eq("user_id", user_id).execute()

            return True
        except Exception as e:
            print(f"Error updating transaction category: {str(e)}")
            return False
    
    def delete_all_transactions(self, user_id: str) -> bool:
        """
        Delete all transactions for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            bool: True if successful
        """
        if not self.client:
            return False
        
        try:
            self.client.table("transactions").delete().eq("user_id", user_id).execute()
            return True
        except Exception as e:
            print(f"Error deleting transactions: {str(e)}")
            return False
    
    # ========================================================================
    # CATEGORY OPERATIONS
    # ========================================================================
    
    def get_categories(self, user_id: str) -> List[Dict]:
        """
        Get all categories for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            List of category dictionaries
        """
        if not self.client:
            return []
        
        try:
            response = self.client.table("categories").select("*").eq("user_id", user_id).execute()
            return response.data
        except Exception as e:
            print(f"Error fetching categories: {str(e)}")
            return []
    
    def get_category_by_name(self, name: str, user_id: str) -> Optional[Dict]:
        """Get a specific category by name."""
        if not self.client:
            return None
        try:
            response = self.client.table("categories").select("*").eq("user_id", user_id).eq("name", name).execute()
            if response.data:
                return response.data[0]
            return None
        except:
            return None

    def create_category(self, category: Category, user_id: str) -> Optional[str]:
        """
        Create a new category.
        
        Returns:
            The ID of the category (newly created or existing)
        """
        if not self.client:
            return None
        
        try:
            # Check if it already exists
            existing = self.get_category_by_name(category.name, user_id)
            if existing:
                return existing['id']
                
            data = category.to_dict()
            data["user_id"] = user_id
            response = self.client.table("categories").insert(data).execute()
            if response.data:
                return response.data[0]['id']
            return None
        except Exception as e:
            print(f"Error creating category: {str(e)}")
            return None

    def update_category_percentage(self, category_id: str, percentage: int, user_id: str) -> bool:
        """Update the budget percentage for a category."""
        if not self.client:
            return False
        try:
            self.client.table("categories").update(
                {"percentage": percentage}
            ).eq("id", category_id).eq("user_id", user_id).execute()
            return True
        except Exception as e:
            print(f"Error updating category percentage: {str(e)}")
            return False
    
    def update_category_rules(self, category_id: str, rules: List[Dict], user_id: str) -> bool:
        """
        Update the rules for a category.
        
        Args:
            category_id: Category ID
            rules: New rules list
            user_id: User ID for verification
            
        Returns:
            bool: True if successful
        """
        if not self.client:
            return False
        
        try:
            self.client.table("categories").update(
                {"rules": rules}
            ).eq("id", category_id).eq("user_id", user_id).execute()
            return True
        except Exception as e:
            print(f"Error updating category rules: {str(e)}")
            return False
    
    # ========================================================================
    # USER PREFERENCES OPERATIONS
    # ========================================================================
    
    def get_user_preferences(self, user_id: str) -> Optional[Dict]:
        """
        Get user preferences.
        
        Args:
            user_id: User ID
            
        Returns:
            Preferences dictionary or None
        """
        if not self.client:
            return None
        
        try:
            response = self.client.table("user_preferences").select("*").eq("user_id", user_id).execute()
            if response.data:
                return response.data[0]
            return None
        except Exception as e:
            print(f"Error fetching preferences: {str(e)}")
            return None
    
    def create_or_update_preferences(self, user_id: str, preferences: Dict) -> bool:
        """
        Create or update user preferences.
        
        Args:
            user_id: User ID
            preferences: Preferences dictionary
            
        Returns:
            bool: True if successful
        """
        if not self.client:
            return False
        
        try:
            preferences["user_id"] = user_id
            
            # Try to get existing preferences
            existing = self.get_user_preferences(user_id)
            
            if existing:
                # Update
                self.client.table("user_preferences").update(preferences).eq("user_id", user_id).execute()
            else:
                # Insert
                self.client.table("user_preferences").insert(preferences).execute()
            
            return True
        except Exception as e:
            print(f"Error saving preferences: {str(e)}")
            return False

    def get_or_create_user(self, user_id: str, email: str, first_name: str, second_name: str, password: Optional[str] = None):
        """
        Ensure user exists in the custom user table.
        """
        if not self.client:
            return None
        
        try:
            # Check if user exists
            response = self.client.table("user").select("*").eq("id", user_id).execute()
            if response.data:
                return response.data[0]
            
            # Create if not
            user_data = {
                "id": user_id,
                "email": email,
                "first_name": first_name,
                "second_name": second_name,
                "password": password or "SSO_USER"
            }
            response = self.client.table("user").insert(user_data).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"Error ensuring user exists: {str(e)}")
            return None

    def migrate_transaction_hashes(self, user_id: str) -> Dict:
        """
        Utility to re-calculate and update all transaction hashes for a user.
        Useful when the hash logic changes.
        """
        if not self.client:
            return {"success": 0, "duplicates_removed": 0, "errors": ["No DB connection"]}

        try:
            # Fetch all transactions for this user
            response = self.client.table("transactions").select("*").eq("user_id", user_id).execute()
            transactions_data = response.data
            
            if not transactions_data:
                return {"success": 0, "duplicates_removed": 0, "errors": []}

            updated_count = 0
            duplicates_removed = 0
            errors = []
            
            # Track hashes we've already processed in this run to detect immediate duplicates
            processed_hashes = {} # hash -> id

            for trans_data in transactions_data:
                try:
                    # Create temporary Transaction object from DB data
                    from decimal import Decimal
                    from models.transaction import Transaction
                    from datetime import datetime
                    
                    t = Transaction(
                        datum=datetime.strptime(trans_data['datum'], '%Y-%m-%d').date() if isinstance(trans_data['datum'], str) else trans_data['datum'],
                        bedrag=Decimal(str(trans_data['bedrag'])),
                        naam_tegenpartij=trans_data.get('naam_tegenpartij'),
                        omschrijving=trans_data.get('omschrijving')
                    )
                    new_hash = t.generate_hash()

                    # Check if this hash is already present in this run OR in DB (for other IDs)
                    if new_hash in processed_hashes:
                        # This record is a duplicate of one we just processed
                        self.client.table("transactions").delete().eq("id", trans_data['id']).execute()
                        duplicates_removed += 1
                        continue
                    
                    # Update DB
                    update_resp = self.client.table("transactions").update({"hash": new_hash}).eq("id", trans_data['id']).execute()
                    
                    if update_resp.data:
                        updated_count += 1
                        processed_hashes[new_hash] = trans_data['id']
                    else:
                        # Duplicate conflict
                        self.client.table("transactions").delete().eq("id", trans_data['id']).execute()
                        duplicates_removed += 1

                except Exception as e:
                    errors.append(f"Error migrating {trans_data.get('id')}: {str(e)}")

            return {
                "success": updated_count,
                "duplicates_removed": duplicates_removed,
                "errors": errors
            }
        except Exception as e:
            return {"success": 0, "duplicates_removed": 0, "errors": [str(e)]}

    def create_user(self, email: str, password: str, first_name: str, second_name: str) -> Tuple[Optional[Dict], Optional[str]]:
        """
        Create a new user account.
        
        Returns:
            Tuple of (user_record, error_message)
        """
        if not self.client:
            return None, "Geen verbinding met de database"
        
        try:
            user_data = {
                "email": email,
                "password": password,
                "first_name": first_name,
                "second_name": second_name
            }
            response = self.client.table("user").insert(user_data).execute()
            if response.data:
                return response.data[0], None
            return None, "Kon gebruiker niet aanmaken"
        except Exception as e:
            error_msg = str(e)
            if "duplicate" in error_msg.lower():
                return None, "Dit e-mailadres is al in gebruik"
            return None, f"Fout bij aanmaken gebruiker: {error_msg}"

    def get_user_by_email(self, email: str) -> Optional[Dict]:
        """Retrieve a user by their email address."""
        if not self.client:
            return None
        try:
            response = self.client.table("user").select("*").eq("email", email).execute()
            if response.data:
                return response.data[0]
            return None
        except Exception as e:
            print(f"Error fetching user by email: {str(e)}")
            return None
