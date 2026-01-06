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

# Default Categories and Rules
DEFAULT_CATEGORIES = {
    "Investeren": {
        "rules": [
            {"field": "naam_tegenpartij", "contains": ["Saxo", "Bolero", "DeGiro", "Beleggen", "Aandelen", "Crypto"]},
        ],
        "color": "#10b981"  # Green
    },
    "Eten & Drinken": {
        "rules": [
            {"field": "naam_tegenpartij", "contains": ["Delhaize", "Restaurant De Brug", "Albert Heijn", "Colruyt", "Carrefour", "Aldi", "Lidl"]},
        ],
        "color": "#f59e0b"  # Orange
    },
    "Transport": {
        "rules": [
            {"field": "naam_tegenpartij", "contains": ["NMBS", "De Lijn", "STIB", "MIVB", "Uber", "Taxi", "Shell", "Total", "Parking"]},
        ],
        "color": "#06b6d4"  # Cyan
    },
    "Inkomen": {
        "rules": [
            {"field": "naam_tegenpartij", "contains": ["Idefix", "Mama en Papa", "Salaris", "Loon"]},
            {"field": "bedrag", "condition": "positive"}
        ],
        "color": "#3b82f6"  # Blue
    },
    "Vrije Tijd": {
        "rules": [
            {"field": "naam_tegenpartij", "contains": ["Cinema", "Theater", "Netflix", "Spotify", "Kinepolis", "UGC"]},
        ],
        "color": "#8b5cf6"  # Purple
    },
    "Sport & Gezondheid": {
        "rules": [
            {"field": "naam_tegenpartij", "contains": ["Basic-Fit", "Fitness", "Gym", "Apotheek", "Pharmacy"]},
        ],
        "color": "#ef4444"  # Red
    },
    "Wonen": {
        "rules": [
            {"field": "naam_tegenpartij", "contains": ["Huur", "Electrabel", "Engie", "Proximus", "Telenet", "Water", "Gas", "Elektriciteit"]},
        ],
        "color": "#64748b"  # Slate
    },
    "Kleding": {
        "rules": [
            {"field": "naam_tegenpartij", "contains": ["H&M", "Zara", "C&A", "Primark", "Bershka", "Mango"]},
        ],
        "color": "#ec4899"  # Pink
    },
    "Reizen": {
        "rules": [
            {"field": "naam_tegenpartij", "contains": ["Booking", "Airbnb", "Ryanair", "Brussels Airlines", "Hotel"]},
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
    "font_family": "Inter, sans-serif"
}
