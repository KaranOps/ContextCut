import asyncio
import os
import sys
import logging
import json

# Add backend to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

# Load .env before settings
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env_path = os.path.join(backend_dir, ".env")
try:
    load_dotenv(env_path, encoding="utf-8")
except UnicodeDecodeError:
    print(".env is not UTF-8, trying UTF-16...")
    load_dotenv(env_path, encoding="utf-16")

from app.services.translation_service import TranslationService
from app.core.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_translation():
    # Load env vars if not already loaded
    if not settings.GROQ_API_KEY and not settings.OPENAI_API_KEY:
        logger.error("No API keys found in settings! Please check .env")
        return

    # Debug API Keys
    print(f"Groq API Key Present: {bool(settings.GROQ_API_KEY)}")
    print(f"OpenAI API Key Present: {bool(settings.OPENAI_API_KEY)}")

    service = TranslationService()

    # Define paths relative to project root
    # settings.DATA_DIR might be relative and context-dependent, so we resolve absolutely
    project_root = os.path.dirname(backend_dir)
    data_dir = os.path.join(project_root, "data")
    
    input_file = os.path.join(data_dir, "processed", "transcription_result_groq.json")
    output_file = os.path.join(data_dir, "processed", "final_transcription_result_gpt-oss-120b.json")

    # Read Input
    if not os.path.exists(input_file):
        print(f"Error: Input file not found at {input_file}")
        # Fallback to creating a dummy one for testing if it doesn't exist? 
        # User implies it exists.
        return

    print(f"Reading from {input_file}...")
    with open(input_file, "r", encoding="utf-8") as f:
        input_data = json.load(f)

    # Validate structure
    segments = input_data.get("segments", [])
    if not segments:
        print("No segments found in input file.")
        return
    
    print(f"Found {len(segments)} segments. Translating...")

    try:
        translated_segments = await service.translate_segments(segments)
        
        # Construct Final Output
        # Combine translated text for the full text field
        full_translated_text = " ".join([seg.get("text", "") for seg in translated_segments])
        
        output_data = {
            "text": full_translated_text,
            "segments": translated_segments
        }

        print(f"Writing output to {output_file}...")
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)

        print("Translation Test Passed! Output saved.")

    except Exception as e:
        print(f"Translation Test Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_translation())
