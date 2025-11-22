#!/usr/bin/env python3
"""Test Gemini API directly"""
import os
import sys
sys.path.append('.')

from app.providers.llm.gemini_llm_client import GeminiLLMClient
from app.config import settings

def test_gemini():
    print(f"API Key exists: {bool(settings.GEMINI_API_KEY)}")

    if not settings.GEMINI_API_KEY:
        print("No API key configured")
        return

    client = GeminiLLMClient(api_key=settings.GEMINI_API_KEY)

    print("Testing Gemini API...")
    try:
        response = client.generate_text(
            messages=[
                {"role": "system", "content": "Return a simple JSON: {\"test\": \"hello\"}"},
                {"role": "user", "content": "test"}
            ],
            temperature=0.5,
            max_tokens=100,
            json_mode=True
        )
        print(f"Success! Response: {response}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_gemini()