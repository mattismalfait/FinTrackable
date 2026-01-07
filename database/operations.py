"""
Database operations for transactions, categories, and user preferences.
"""

from typing import List, Optional, Dict
from datetime import date, datetime
from database.connection import get_supabase_client
from models.transaction import Transaction
from models.category import Category
import streamlit as st

class DatabaseOperations:
    """Handle all database CRUD operations."""
    
    def __init__(self):
        self.client = get_supabase_client()
    
    # ========================================================================
    # TRANSACTION OPERATIONS
    # ========================================================================
    
    def get_existing_hashes(self, user_id: str) -> set:
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
            # We use a large limit to get everything (Supabase default is 1000)
            # You might need pagination for huge datasets, but for personal finance this works for now
            response = self.client.table("transactions").select("hash").eq("user_id", user_id).limit(10000).execute()
            
            return {item['hash'] for item in response.data if item.get('hash')}
        except Exception as e:
            st.error(f"Error checking duplicates: {str(e)}")
            return set()

    def insert_transactions(self, transactions: List[Transaction], user_id: str) -> Dict:
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
        
        # If we didn't filter before calling this function, we do it here one by one (slow)
        # But ideally, we should use get_existing_hashes before
        
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
                # If category is provided as a name, we might need a separate query or handle it by ID
                # For now, we'll assume filter by ID if it's a UUID, otherwise by name via join
                if len(category) > 30 and "-" in category: # Simple UUID check
                    query = query.eq("categorie_id", category)
                else:
                    # Filter by category name in the joined table
                    # Note: Supabase filtering on joined tables can be tricky, 
                    # but usually it's 'categories.name'
                    query = query.eq("categories.name", category)
                    
            if is_confirmed is not None:
                query = query.eq("is_confirmed", is_confirmed)
            
            # Order by date descending
            query = query.order("datum", desc=True)
            
            response = query.execute()
            
            # Flatten the response for easier use
            processed_data = []
            for item in response.data:
                category_info = item.get('categories', {})
                if category_info:
                    item['categorie'] = category_info.get('name', 'Overig')
                    item['color'] = category_info.get('color', '#9ca3af')
                else:
                    item['categorie'] = 'Overig'
                    item['color'] = '#9ca3af'
                processed_data.append(item)
                
            return processed_data
        except Exception as e:
            st.error(f"Error fetching transactions: {str(e)}")
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
            st.error(f"Error confirming transaction: {str(e)}")
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
            st.error(f"Error updating transaction: {str(e)}")
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
            response = self.client.table("transactions").delete().eq("id", transaction_id).eq("user_id", user_id).execute()
            return True
        except Exception as e:
            st.error(f"Error deleting transaction: {str(e)}")
            return False

    def update_transaction_category(self, transaction_id: str, category_id: str, user_id: str) -> bool:
        """
        Update the category ID of a transaction.
        
        Args:
            transaction_id: Transaction ID
            category_id: New category ID
            user_id: User ID for verification
            
        Returns:
            bool: True if successful
        """
        if not self.client:
            return False
        
        try:
            self.client.table("transactions").update(
                {"categorie_id": category_id}
            ).eq("id", transaction_id).eq("user_id", user_id).execute()
            return True
        except Exception as e:
            st.error(f"Error updating transaction category: {str(e)}")
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
            st.error(f"Error deleting transactions: {str(e)}")
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
            st.error(f"Error fetching categories: {str(e)}")
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
            st.error(f"Error creating category: {str(e)}")
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
            st.error(f"Error updating category percentage: {str(e)}")
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
            st.error(f"Error updating category rules: {str(e)}")
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
            st.error(f"Error fetching preferences: {str(e)}")
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
            st.error(f"Error saving preferences: {str(e)}")
            return False

    def get_or_create_user(self, user_id: str, email: str, first_name: str, second_name: str, password: Optional[str] = None) -> Optional[Dict]:
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
            
            # Create user if doesn't exist
            user_data = {
                "id": user_id,
                "email": email,
                "first_name": first_name,
                "second_name": second_name
            }
            if password:
                user_data["password"] = password
                
            response = self.client.table("user").insert(user_data).execute()
            if response.data:
                return response.data[0]
            return None
        except Exception as e:
            print(f"Custom user table access error: {str(e)}")
            return {"id": user_id, "email": email, "first_name": first_name, "second_name": second_name}

    def create_user(self, email: str, password: str, first_name: str, second_name: str) -> tuple[Optional[Dict], Optional[str]]:
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
