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
            query = self.client.table("transactions").select("*").eq("user_id", user_id)
            
            if start_date:
                query = query.gte("datum", start_date.isoformat())
            if end_date:
                query = query.lte("datum", end_date.isoformat())
            if category:
                query = query.eq("categorie", category)
            if is_confirmed is not None:
                query = query.eq("is_confirmed", is_confirmed)
            
            # Order by date descending
            query = query.order("datum", desc=True)
            
            response = query.execute()
            return response.data
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

    def update_transaction_category(self, transaction_id: str, category: str, user_id: str) -> bool:
        """
        Update the category of a transaction.
        
        Args:
            transaction_id: Transaction ID
            category: New category name
            user_id: User ID for verification
            
        Returns:
            bool: True if successful
        """
        if not self.client:
            return False
        
        try:
            self.client.table("transactions").update(
                {"categorie": category}
            ).eq("id", transaction_id).eq("user_id", user_id).execute()
            return True
        except Exception as e:
            st.error(f"Error updating transaction: {str(e)}")
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

    def create_category(self, category: Category, user_id: str) -> bool:
        """
        Create a new category.
        
        Args:
            category: Category object
            user_id: User ID
            
        Returns:
            bool: True if successful
        """
        if not self.client:
            return False
        
        try:
            data = category.to_dict()
            data["user_id"] = user_id
            self.client.table("categories").insert(data).execute()
            return True
        except Exception as e:
            # Check if it already exists
            existing = self.get_category_by_name(category.name, user_id)
            if existing:
                return True # Treat as success if it already exists
            st.error(f"Error creating category: {str(e)}")
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
