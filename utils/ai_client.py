"""
Unified AI client for FinTrackable.
Supports Huggingface (via OpenAI client) and Google Gemini.
"""
import logging
import streamlit as st
from openai import OpenAI
from google import genai
from config.settings import GEMINI_API_KEY, HF_TOKEN, HF_MODEL, HF_BASE_URL

logger = logging.getLogger(__name__)

class AIClient:
    def __init__(self):
        self.provider = None
        self.client = None
        self.model_name = None
        self.enabled = False
        
        if HF_TOKEN:
            logger.info(f"AI: Using Huggingface Token with model {HF_MODEL}")
            self.client = OpenAI(
                base_url=HF_BASE_URL,
                api_key=HF_TOKEN,
            )
            self.model_name = HF_MODEL
            self.provider = "hf"
            self.enabled = True
        elif GEMINI_API_KEY:
            logger.info("AI: Falling back to Gemini API")
            try:
                self.client = genai.Client(api_key=GEMINI_API_KEY)
                self.model_name = 'gemini-flash-latest'
                self.provider = "gemini"
                self.enabled = True
            except Exception as e:
                logger.error(f"AI: Gemini initialization failed: {str(e)}")
        else:
            logger.warning("AI: No credentials found. AI features will be disabled.")

    def generate_content(self, prompt: str) -> str:
        """Utility to get text response from configured provider."""
        if not self.enabled:
            return ""
            
        try:
            if self.provider == "hf":
                completion = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[{"role": "user", "content": prompt}],
                )
                return completion.choices[0].message.content
            elif self.provider == "gemini":
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt
                )
                return response.text
        except Exception as e:
            logger.error(f"AI Error ({self.provider}): {str(e)}")
            raise e
        return ""
