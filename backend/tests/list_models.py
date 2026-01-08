import os
import sys
from dotenv import load_dotenv
from openai import OpenAI

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
load_dotenv(os.path.join(os.path.dirname(__file__), "../.env"), encoding="utf-16")

from app.core.config import settings

def main():
    try:
        client = OpenAI(
            api_key=settings.GROQ_API_KEY,
            base_url="https://api.groq.com/openai/v1"
        )
        models = client.models.list()
        print("Available Groq Models:")
        for m in models.data:
            print(f"- {m.id}")
            
    except Exception as e:
        print(f"Error listing models: {e}")

if __name__ == "__main__":
    main()
