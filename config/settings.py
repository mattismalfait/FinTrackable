"""
Configuration settings for FinTrackable application.
Handles environment variables and application constants.
"""

import os
from dotenv import load_dotenv
from typing import List, Dict

# Load environment variables
load_dotenv()

# Supabase Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

# AI Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", os.getenv("GOOGLE_API_KEY", ""))
HF_TOKEN = os.getenv("HF_TOKEN", "")
HF_MODEL = os.getenv("HF_MODEL", "moonshotai/Kimi-K2-Instruct-0905")
HF_BASE_URL = "https://router.huggingface.co/v1"


# Application Settings
APP_NAME = os.getenv("APP_NAME", "FinTrackable")
DEFAULT_INVESTMENT_GOAL = float(os.getenv("DEFAULT_INVESTMENT_GOAL", "20"))

# CSV Column Names (KBC format)
CSV_COLUMNS = {
    "datum": "Datum",
    "bedrag": "Bedrag",
    "naam_tegenpartij": "Naam tegenpartij",
    "omschrijving": "Omschrijving"
}

# Default Categories and Rules (International Keywords Support)
DEFAULT_CATEGORIES = {
    "Investeren": {
        "rules": [
            {"field": "naam_tegenpartij", "contains": ["Saxo", "Bolero", "DeGiro", "Beleggen", "Aandelen", "Crypto", "Investment", "Trading", "Stocks", "Bourse"]},
        ],
        "color": "#10b981"  # Green
    },
    "Eten & Drinken": {
        "rules": [
            {"field": "naam_tegenpartij", "contains": ["Delhaize", "Restaurant", "Albert Heijn", "Colruyt", "Carrefour", "Aldi", "Lidl", "Jumbo", "Waitrose", "Tesco", "Uber Eats", "Deliveroo", "Food", "Supermarket"]},
        ],
        "color": "#f59e0b"  # Orange
    },
    "Transport": {
        "rules": [
            {"field": "naam_tegenpartij", "contains": ["NMBS", "De Lijn", "STIB", "MIVB", "Uber", "Taxi", "Shell", "Total", "Parking", "Train", "SNCF", "NS", "Bolt", "Gas Station", "Petrol"]},
        ],
        "color": "#06b6d4"  # Cyan
    },
    "Inkomen": {
        "rules": [
            {"field": "naam_tegenpartij", "contains": ["Salaris", "Loon", "Salary", "Income", "Wage", "Dividend", "Salaire"]},
            {"field": "bedrag", "condition": "positive"}
        ],
        "color": "#3b82f6"  # Blue
    },
    "Vrije Tijd": {
        "rules": [
            {"field": "naam_tegenpartij", "contains": ["Cinema", "Theater", "Netflix", "Spotify", "Kinepolis", "UGC", "Leisure", "Game", "Steam", "Disney+"]},
        ],
        "color": "#8b5cf6"  # Purple
    },
    "Sport & Gezondheid": {
        "rules": [
            {"field": "naam_tegenpartij", "contains": ["Basic-Fit", "Fitness", "Gym", "Apotheek", "Pharmacy", "Health", "Hospital", "Doctor", "Apotheke", "Pharmacie"]},
        ],
        "color": "#ef4444"  # Red
    },
    "Wonen": {
        "rules": [
            {"field": "naam_tegenpartij", "contains": ["Huur", "Electrabel", "Engie", "Proximus", "Telenet", "Water", "Gas", "Elektriciteit", "Rent", "Utility", "Loyer", "Mieten", "Electricity"]},
        ],
        "color": "#64748b"  # Slate
    },
    "Kleding": {
        "rules": [
            {"field": "naam_tegenpartij", "contains": ["H&M", "Zara", "C&A", "Primark", "Bershka", "Mango", "Clothing", "Fashion", "Zalando", "ASOS"]},
        ],
        "color": "#ec4899"  # Pink
    },
    "Reizen": {
        "rules": [
            {"field": "naam_tegenpartij", "contains": ["Booking", "Airbnb", "Ryanair", "Brussels Airlines", "Hotel", "Travel", "Flight", "Voyage", "Reise"]},
        ],
        "color": "#14b8a6"  # Teal
    },
    "Overig": {
        "rules": [],
        "color": "#9ca3af"  # Gray
    }
}

# Date Format Settings
DATE_FORMATS = [
    "%d/%m/%Y",
    "%Y-%m-%d",
    "%d-%m-%Y",
    "%m/%d/%Y"
]

# UI Theme Colors
THEME_COLORS = {
    "primary": "#1e40af",
    "secondary": "#64748b",
    "success": "#10b981",
    "warning": "#f59e0b",
    "danger": "#ef4444",
    "income": "#3b82f6",
    "expense": "#ef4444"
}

# Chart Configuration
CHART_CONFIG = {
    "height": 400,
    "margin": {"l": 50, "r": 50, "t": 50, "b": 50},
    "font_family": "Manrope, sans-serif"
}
