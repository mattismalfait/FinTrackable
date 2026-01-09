import os
import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_hf_router():
    token = os.environ.get("HF_TOKEN")
    if not token:
        print("❌ HF_TOKEN not found in environment.")
        return

    print(f"✅ HF_TOKEN found. Testing Huggingface Router...")
    
    client = OpenAI(
        base_url="https://router.huggingface.co/v1",
        api_key=token,
    )

    try:
        completion = client.chat.completions.create(
            model="moonshotai/Kimi-K2-Instruct-0905",
            messages=[
                {
                    "role": "user",
                    "content": "Generate a list of 3 interesting facts about space."
                }
            ],
        )

        print("\n🤖 AI Response:")
        print(completion.choices[0].message.content)
        print("\n✅ Verification successful!")
    except Exception as e:
        print(f"\n❌ Error during verification: {str(e)}")

if __name__ == "__main__":
    test_hf_router()
