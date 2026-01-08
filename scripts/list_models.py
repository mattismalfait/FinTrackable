
import os
from dotenv import load_dotenv
from google import genai

def list_models():
    load_dotenv()
    key = os.getenv("GEMINI_API_KEY")
    client = genai.Client(api_key=key)
    
    try:
        print("Listing available models...")
        for model in client.models.list():
            print(f"- {model.name}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    list_models()
