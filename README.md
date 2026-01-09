# 🏦 FinTrackable

TypeError: Failed to fetch dynamically imported module: https://fintrackable.onrender.com/static/js/index.CV56Xzvw.js

**Financiële Administratie Geautomatiseerd**

Een volledige, productie-klare financiële administratie-applicatie die KBC banktransacties automatisch verwerkt, categoriseert en visualiseert. Vervang je manuele Excel-administratie door een geautomatiseerde oplossing met een gebruiksvriendelijke Streamlit-interface.

![Dashboard](https://img.shields.io/badge/Dashboard-Streamlit-FF4B4B)
![Database](https://img.shields.io/badge/Database-Supabase-3ECF8E)
![Python](https://img.shields.io/badge/Python-3.9+-blue)

## ✨ Functionaliteiten

### 📤 CSV Import & Verwerking
- Upload KBC CSV-bestanden met automatische encodingdetectie
- Intelligente duplicaatdetectie bij overlappende periodes
- Robuuste foutafhandeling voor ontbrekende of incorrecte data
- Preview functie voordat je importeert

### 🏷️ Automatische Categorisatie
- Intelligente regelgebaseerde categorisatie op basis van tegenpartij en omschrijving
- Standaard categorieën: Investeren, Eten, Gym, Inkomen, Vrije Tijd, Reizen, Wonen
- Leerbaar systeem: onbekende transacties vragen om input en onthouden je keuze
- Handmatige aanpassing van categorisatieregels mogelijk

### 📊 Dashboard & Visualisaties
- Maandelijkse trendanalyse per categorie
- Inkomsten vs. uitgaven met netto overzicht
- Beleggingsdoelen tracking met percentage visualisatie
- Jaaroverzicht met vergelijkingen tussen jaren
- Interactieve filters voor datum en categorie
- Categorie breakdown met donut chart
- Top uitgaven overzicht

### 🔐 Veiligheid & Privacy
- Gebruikersauthenticatie via Supabase Auth
- Row Level Security (RLS) - elk gebruiker ziet alleen eigen data
- Veilige opslag van financiële gegevens
- Geen delen van data tussen gebruikers

## 🚀 Installatie

### Vereisten

- Python 3.9 of hoger
- Supabase account (gratis tier beschikbaar op [supabase.com](https://supabase.com))
- Git (optioneel)

### Stap 1: Clone Repository

```bash
git clone <repository-url>
cd FinTrackable
```

Of download de bestanden handmatig.

### Stap 2: Virtual Environment Aanmaken

**Windows (PowerShell):**
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

**Windows (CMD):**
```cmd
python -m venv .venv
.venv\Scripts\activate.bat
```

**macOS/Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Stap 3: Dependencies Installeren

```bash
pip install -r requirements.txt
```

### Stap 4: Supabase Setup

1. **Maak een Supabase project aan:**
   - Ga naar [supabase.com](https://supabase.com)
   - Klik op "New Project"
   - Kies een naam en wachtwoord voor je database

2. **Voer database schema uit:**
   - Open de Supabase SQL Editor
   - Kopieer de inhoud van `database/schema.sql`
   - Voer het script uit

3. **Haal je credentials op:**
   - Ga naar Project Settings → API
   - Kopieer je `Project URL` en `anon/public key`

### Stap 5: Configuratie

1. Kopieer `.env.example` naar `.env`:
   ```bash
   copy .env.example .env  # Windows
   cp .env.example .env    # macOS/Linux
   ```

2. Bewerk `.env` en vul je Supabase credentials in:
   ```
   SUPABASE_URL=jouw-project-url.supabase.co
   SUPABASE_KEY=jouw-anon-key
   
   APP_NAME=FinTrackable
   DEFAULT_INVESTMENT_GOAL=20
   ```

### Stap 6: Applicatie Starten

```bash
streamlit run app.py
```

De applicatie opent automatisch in je browser op `http://localhost:8501`

## 📖 Gebruik

### 1. Account Aanmaken

Bij eerste gebruik:
1. Ga naar de "Registreren" tab
2. Vul je e-mail en wachtwoord in
3. Klik op "Registreren"
4. Log in met je nieuwe account

### 2. CSV Importeren

1. Exporteer je KBC banktransacties als CSV
2. Ga naar "📤 CSV Importeren" in het menu
3. Upload je CSV-bestand
4. Controleer de preview en automatische categorisatie
5. Klik op "✅ Importeren"

**Verwachte CSV-formaat:**
| Datum | Bedrag | Naam tegenpartij | Omschrijving |
|-------|--------|------------------|--------------|
| 01/01/2025 | -45.50 | Delhaize | ... |
| 02/01/2025 | 2500.00 | Werkgever | ... |

### 3. Dashboard Bekijken

Het dashboard toont automatisch:
- **Belangrijkste cijfers**: Totale inkomsten, uitgaven, netto saldo, investeringspercentage
- **Overzicht tab**: Inkomsten vs uitgaven grafiek + categorie breakdown
- **Trends tab**: Maandelijkse trends per categorie
- **Investeringen tab**: Tracking van investeringsdoelen
- **Jaarlijks tab**: Vergelijking tussen verschillende jaren

### 4. Categorieën Beheren

In "🏷️ Categorieën":
- **Transacties controleren**: Bekijk en corrigeer categorieën
- **Regels beheren**: Bekijk automatische categorisatieregels
- **Nieuwe categorie**: Voeg eigen categorieën toe

### 5. Instellingen

In "⚙️ Instellingen":
- Stel je investeringsdoel in (percentage van inkomen)
- Bekijk account informatie
- Verwijder alle transacties (gevaarlijk!)

## 🏗️ Projectstructuur

```
FinTrackable/
├── app.py                      # Hoofdapplicatie
├── requirements.txt            # Python dependencies
├── .env                        # Configuratie (niet committen!)
├── config/
│   └── settings.py            # App configuratie
├── database/
│   ├── connection.py          # Supabase verbinding
│   ├── operations.py          # Database CRUD operaties
│   └── schema.sql             # Database schema
├── models/
│   ├── transaction.py         # Transaction model
│   └── category.py            # Category model
├── services/
│   ├── csv_parser.py          # CSV parsing logica
│   ├── categorization.py      # Categorisatie engine
│   └── analytics.py           # Data analytics
└── ui/
    ├── auth.py                # Authenticatie UI
    ├── dashboard.py           # Hoofddashboard
    ├── upload.py              # CSV upload interface
    ├── categorization_review.py  # Categorieën beheren
    └── visualizations.py      # Plotly grafieken
```

## 🛠️ Technische Details

### Tech Stack

- **Framework**: Streamlit 1.31+
- **Database**: Supabase (PostgreSQL)
- **Data Processing**: Pandas 2.1+
- **Visualizations**: Plotly 5.18+
- **Validation**: Pydantic 2.5+

### Default Categorieën

| Categorie | Voorbeelden | Kleur |
|-----------|------------|-------|
| Investeren | Saxo, Mattis Henriette | Groen |
| Eten | Delhaize, Colruyt, Restaurants | Oranje |
| Gym | Basic-Fit | Rood |
| Inkomen | Werkgever, Positieve bedragen | Blauw |
| Vrije Tijd | Netflix, Cinema, Spotify | Paars |
| Reizen | NMBS, Ryanair, Hotels | Cyaan |
| Wonen | Huur, Electrabel, Internet | Grijs |
| Overig | Niet gecategoriseerd | Lichtgrijs |

## 🐛 Troubleshooting

### "Supabase is niet geconfigureerd"
- Controleer of je `.env` bestand bestaat
- Controleer of `SUPABASE_URL` en `SUPABASE_KEY` correct zijn ingevuld

### "Database connection test failed"
- Controleer je internetverbinding
- Controleer of je Supabase project actief is
- Controleer of het database schema correct is uitgevoerd

### "Permission denied" bij virtual environment
- Windows: Voer `Set-ExecutionPolicy RemoteSigned -Scope CurrentUser` uit in PowerShell
- Probeer CMD in plaats van PowerShell

### CSV upload faalt
- Controleer of het bestand daadwerkelijk CSV formaat is
- Controleer of alle verplichte kolommen aanwezig zijn
- Controleer encoding (probeer opslaan als UTF-8)

## 📝 Licentie

Dit project is beschikbaar voor persoonlijk gebruik.

## 🤝 Contributing

Feedback en suggesties zijn welkom! Open een issue of pull request.

## 📧 Contact

Voor vragen of ondersteuning, neem contact op via de GitHub issues.

---

**Gemaakt met ❤️ voor betere financiële administratie**
