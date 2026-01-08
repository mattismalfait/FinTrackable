
import os
from dotenv import load_dotenv
from google import genai

def verify():
    load_dotenv()
    key = os.getenv("GEMINI_API_KEY")
    client = genai.Client(api_key=key)
    
    try:
        model_id = 'gemini-flash-latest' 
        print(f"Testing with model: {model_id}")
        
        response = client.models.generate_content(
            model=model_id,
            contents="Say 'Latest Flash OK'"
        )
        print(f"Result: {response.text.strip()}")
    except Exception as e:
        print(f"Fail: {e}")

if __name__ == "__main__":
    verify()
