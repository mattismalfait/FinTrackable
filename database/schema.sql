-- FinTrackable Database Schema for Supabase
-- This file contains all table definitions and security policies

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- TABLES
-- ============================================================================

-- Transactions Table
CREATE TABLE IF NOT EXISTS transactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    datum DATE NOT NULL,
    bedrag DECIMAL(12, 2) NOT NULL,
    naam_tegenpartij TEXT,
    omschrijving TEXT,
    categorie TEXT,
    hash TEXT UNIQUE NOT NULL, -- For duplicate detection
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create index for faster queries
CREATE INDEX IF NOT EXISTS idx_transactions_user_id ON transactions(user_id);
CREATE INDEX IF NOT EXISTS idx_transactions_datum ON transactions(datum);
CREATE INDEX IF NOT EXISTS idx_transactions_categorie ON transactions(categorie);
CREATE INDEX IF NOT EXISTS idx_transactions_hash ON transactions(hash);

-- Categories Table
CREATE TABLE IF NOT EXISTS categories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    name TEXT NOT NULL,
    rules JSONB DEFAULT '[]'::jsonb,
    color TEXT DEFAULT '#9ca3af',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, name)
);

CREATE INDEX IF NOT EXISTS idx_categories_user_id ON categories(user_id);

-- User Preferences Table
CREATE TABLE IF NOT EXISTS user_preferences (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL UNIQUE,
    investment_goal_percentage DECIMAL(5, 2) DEFAULT 20.00,
    default_categories JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_user_preferences_user_id ON user_preferences(user_id);

-- ============================================================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- ============================================================================

-- Enable RLS on all tables
ALTER TABLE transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE categories ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_preferences ENABLE ROW LEVEL SECURITY;

-- Transactions Policies
CREATE POLICY "Users can view own transactions" 
    ON transactions FOR SELECT 
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own transactions" 
    ON transactions FOR INSERT 
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own transactions" 
    ON transactions FOR UPDATE 
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own transactions" 
    ON transactions FOR DELETE 
    USING (auth.uid() = user_id);

-- Categories Policies
CREATE POLICY "Users can view own categories" 
    ON categories FOR SELECT 
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own categories" 
    ON categories FOR INSERT 
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own categories" 
    ON categories FOR UPDATE 
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own categories" 
    ON categories FOR DELETE 
    USING (auth.uid() = user_id);

-- User Preferences Policies
CREATE POLICY "Users can view own preferences" 
    ON user_preferences FOR SELECT 
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own preferences" 
    ON user_preferences FOR INSERT 
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own preferences" 
    ON user_preferences FOR UPDATE 
    USING (auth.uid() = user_id);

-- ============================================================================
-- FUNCTIONS
-- ============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create triggers for updated_at
CREATE TRIGGER update_transactions_updated_at BEFORE UPDATE ON transactions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_categories_updated_at BEFORE UPDATE ON categories
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_preferences_updated_at BEFORE UPDATE ON user_preferences
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
