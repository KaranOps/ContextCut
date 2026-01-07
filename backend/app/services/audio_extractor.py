import ffmpeg
import logging
import os

# Configure logging
logger = logging.getLogger(__name__)

class AudioExtractor:
    """
    Service for extracting audio from video files, optimized for OpenAI Whisper.
    
    Uses ffmpeg-python to perform audio extraction with specific parameters:
    - Sample Rate: 16kHz
    - Channels: Mono (1)
    - Codec: pcm_s16le (WAV) or mp3
    """

    @staticmethod
    def extract_for_whisper(input_path: str, output_path: str) -> str:
        """
        Extracts audio from a video file and optimizes it for Whisper as a static method.

        Args:
            input_path (str): The absolute path to the input video file.
            output_path (str): The absolute path where the extracted audio should be saved.

        Returns:
            str: The path to the generated audio file.

        Raises:
            RuntimeError: If ffmpeg execution fails.
        """
        logger.info(f"Starting extraction: {input_path} -> {output_path}")

        try:
            # Check if input file exists
            if not os.path.exists(input_path):
                raise FileNotFoundError(f"Input file not found: {input_path}")

            # Ensure the directory for output_path exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            # Construct ffmpeg stream
            # -vn: Disable video
            # -ar 16000: Set audio sampling rate to 16kHz
            # -ac 1: Set audio channels to 1 (Mono)
            # -y: Overwrite output file without asking
            stream = ffmpeg.input(input_path)
            stream = ffmpeg.output(stream, output_path, **{
                'vn': None,
                'ar': '16000',
                'ac': '1',
            }).overwrite_output()

            # Run ffmpeg command
            # capture_stdout=True, capture_stderr=True to capture output for error handling
            stream.run(capture_stdout=True, capture_stderr=True)
            
            logger.info("Audio extraction successful.")
            return output_path

        except ffmpeg.Error as e:
            # Decode stderr to get the actual error message from ffmpeg
            error_message = e.stderr.decode('utf8') if e.stderr else "Unknown ffmpeg error"
            logger.error(f"FFmpeg failed: {error_message}")
            raise RuntimeError(f"FFmpeg failed to extract audio: {error_message}") from e
        except Exception as e:
            logger.error(f"An unexpected error occurred during audio extraction: {str(e)}")
            raise
