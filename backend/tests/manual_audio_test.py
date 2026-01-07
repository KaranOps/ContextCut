import logging
import sys
import os

# Add backend directory to sys.path to allow imports
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
sys.path.append(backend_dir)

from app.services.audio_extractor import AudioExtractor

# Configure logging to stdout
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_audio_extraction():
    # Define paths
    input_video = os.path.join(backend_dir, "..", "data", "uploads", "a_roll.mp4")
    output_audio = os.path.join(backend_dir, "..", "data", "processed", "extracted_audio.mp3")

    # Normalize paths
    input_video = os.path.normpath(input_video)
    output_audio = os.path.normpath(output_audio)

    print(f"Testing Audio Extraction...")
    print(f"Input: {input_video}")
    print(f"Output: {output_audio}")

    try:
        output = AudioExtractor.extract_for_whisper(input_video, output_audio)
        print(f"SUCCESS: Audio extracted to {output}")
    except RuntimeError as e:
        print(f"FAILURE: RuntimeError caught as expected (if ffmpeg is missing/broken): {e}")
    except FileNotFoundError as e:
        print(f"FAILURE: FileNotFoundError: {e}")
    except Exception as e:
        print(f"FAILURE: Unexpected error: {e}")

if __name__ == "__main__":
    test_audio_extraction()
