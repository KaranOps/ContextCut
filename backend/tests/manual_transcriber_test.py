import asyncio
import json
import logging
import sys
import os

# Add backend directory to sys.path to allow imports
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
sys.path.append(backend_dir)

from app.services.transcriber import Transcriber

# Configure logging to stdout
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_transcription():
    transcriber = Transcriber()
    
    # Define paths (pointing to project root data)
    # Assuming audio was extracted to data/processed/extracted_audio.mp3
    input_audio = os.path.join(backend_dir, "..", "data", "processed", "extracted_audio.mp3")
    input_audio = os.path.normpath(input_audio)

    print(f"Testing Transcription Service...")
    print(f"Mode: {'API' if transcriber.use_api else 'Local'}")
    print(f"Input: {input_audio}")

    if not os.path.exists(input_audio):
        print(f"FAILURE: Input file not found: {input_audio}")
        print("Please run manual_audio_test.py first or provide a valid audio file.")
        return

    try:
        output = await transcriber.transcribe(input_audio)
        print("\n--- Transcription Result ---")
        print(f"Full Text: {output['text'][:100]}...") # Print first 100 chars
        print(f"Segments: {len(output['segments'])}")
        if output['segments']:
            print(f"First Segment: {output['segments'][0]}")
        
        # Save output to file
        output_file = os.path.join(backend_dir, "..", "data", "processed", "transcription_result_turbo.json")
        output_file = os.path.normpath(output_file)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=4, ensure_ascii=False)
            
        print(f"SUCCESS: Transcription completed. Output saved to {output_file}")
    except Exception as e:
        print(f"FAILURE: Transcription failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_transcription())
