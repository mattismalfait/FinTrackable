
from dotenv import dotenv_values
import os

def check_env():
    # dotenv_values returns a dict of the variables in .env without loading them into os.environ
    config = dotenv_values(".env")
    print("Keys found in .env:")
    for key in config.keys():
        print(f"- {key}")
    
    # Check what's actually loaded in os.environ after load_dotenv
    from dotenv import load_dotenv
    load_dotenv()
    print("\nKeys in os.environ (filtered):")
    for key in os.environ:
        if "KEY" in key or "URL" in key or "GEMINI" in key:
            print(f"- {key}")

if __name__ == "__main__":
    check_env()
