
import os
import sys
from dotenv import load_dotenv
from google import genai

def test_api():
    # Load .env
    load_dotenv()
    
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    
    if not api_key:
        print("❌ ERROR: No API key found in environment variables.")
        print("Check if .env contains GEMINI_API_KEY=your_key_here")
        return

    print(f"✅ Found API key (starts with: {api_key[:5]}...)")
    
    try:
        client = genai.Client(api_key=api_key)
        print("⏳ Testing connection to Gemini...")
        
        response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents="Say 'API connection successful!'"
        )
        
        if response and response.text:
            print(f"🚀 SUCCESS: {response.text.strip()}")
        else:
            print("⚠️ WARNING: Received empty response from Gemini.")
            
    except Exception as e:
        print(f"❌ ERROR: Failed to connect to Gemini.")
        print(f"Details: {str(e)}")

if __name__ == "__main__":
    test_api()
