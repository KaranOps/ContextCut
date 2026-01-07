import os
import logging
from typing import Dict, Any, List, Optional
import whisper
from openai import AsyncOpenAI
import torch

from app.core.config import settings

logger = logging.getLogger(__name__)

class Transcriber:
    """
    Hybrid transcription service that can switch between OpenAI API and local Whisper model.
    """
    _instance = None
    _model = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Transcriber, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """
        Initializes the Transcriber service.
        Checks for API key to determine mode (API vs Local).
        """
        if settings.OPENAI_API_KEY:
            self.use_api = True
            logger.info("Initializing Transcriber in API Mode (OpenAI).")
            self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        else:
            self.use_api = False
            logger.info(f"Initializing Transcriber in Local Mode. Loading model: {settings.WHISPER_MODEL_SIZE}")
            self._load_local_model()

    def _load_local_model(self):
        """
        Loads the local Whisper model.
        Ensures the model is loaded only once.
        """
        if self._model is None:
            try:
                # Use FP16=False on CPU to avoid warnings
                device = "cuda" if torch.cuda.is_available() else "cpu"
                logger.info(f"Loading Whisper model on device: {device}")
                self._model = whisper.load_model(settings.WHISPER_MODEL_SIZE, device=device)
            except Exception as e:
                logger.error(f"Failed to load local Whisper model: {e}")
                raise RuntimeError(f"Failed to load local Whisper model: {e}")

    async def transcribe(self, audio_path: str) -> Dict[str, Any]:
        """
        Transcribes the given audio file using either OpenAI API or local Whisper model.

        Args:
            audio_path (str): Absolute path to the audio file.

        Returns:
            dict: Standardized dictionary containing text and segments.
                {
                    "text": "Full text...",
                    "segments": [{"start": 0.0, "end": 2.0, "text": "..."}]
                }
        """
        if not os.path.exists(audio_path):
            logger.error(f"Audio file not found: {audio_path}")
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        logger.info(f"Starting transcription for: {audio_path}")

        try:
            if self.use_api:
                return await self._transcribe_api(audio_path)
            else:
                return self._transcribe_local(audio_path)
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            raise RuntimeError(f"Transcription failed: {e}")

    async def _transcribe_api(self, audio_path: str) -> Dict[str, Any]:
        """Transcribes using OpenAI API."""
        try:
            with open(audio_path, "rb") as audio_file:
                transcript = await self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="verbose_json",
                    timestamp_granularities=["segment"]
                )
            
            # The return type of transcriptions.create with verbose_json is an object, not a dict.
            # We need to access attributes.
            
            segments = []
            if hasattr(transcript, 'segments'):
                for seg in transcript.segments:
                    segments.append({
                        "start": seg.start,
                        "end": seg.end,
                        "text": seg.text.strip()
                    })
            
            return {
                "text": transcript.text,
                "segments": segments
            }
        except Exception as e:
            logger.error(f"API Transcription error: {e}")
            raise e

    def _transcribe_local(self, audio_path: str) -> Dict[str, Any]:
        """Transcribes using local Whisper model."""
        try:
            # task="translate" ensures output is in English
            result = self._model.transcribe(audio_path, task="translate", fp16=False)
            
            segments = []
            for seg in result.get("segments", []):
                segments.append({
                    "start": seg["start"],
                    "end": seg["end"],
                    "text": seg["text"].strip()
                })

            return {
                "text": result.get("text", ""),
                "segments": segments
            }
        except Exception as e:
            logger.error(f"Local Transcription error: {e}")
            raise e
