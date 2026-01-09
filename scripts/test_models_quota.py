import os
from google import genai
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY')
client = genai.Client(api_key=api_key)

models_to_test = [
    'gemini-flash-latest',
    'gemini-flash-lite-latest',
]

print("--- Testing specific models ---")
for m in models_to_test:
    try:
        response = client.models.generate_content(model=m, contents="ping")
        print(f"✅ {m}: Success!")
    except Exception as e:
        print(f"❌ {m}: {str(e)[:100]}...")

print("\n--- Listing all models containing 'flash' ---")
try:
    for model in client.models.list():
        if 'flash' in model.name.lower():
            print(f"Found: {model.name}")
except Exception as e:
    print(f"Error listing: {e}")
