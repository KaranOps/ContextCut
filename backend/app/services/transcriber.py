import os
import logging
import json
from typing import Dict, Any, List
import whisper
from openai import AsyncOpenAI
import torch

from app.core.config import settings

logger = logging.getLogger(__name__)

class Transcriber:
    """
    Universal transcription service that prioritizes Groq -> OpenAI -> Local.
    """
    _instance = None
    _model = None
    _local_model_loaded = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Transcriber, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """Initializes API clients."""
        self.groq_client = None
        self.openai_client = None

        if settings.GROQ_API_KEY:
            logger.info("Initializing Groq Client.")
            self.groq_client = AsyncOpenAI(
                base_url="https://api.groq.com/openai/v1",
                api_key=settings.GROQ_API_KEY
            )

        if settings.OPENAI_API_KEY:
            logger.info("Initializing OpenAI Client.")
            self.openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

        logger.info("Transcriber initialized.")

    def _ensure_local_model(self):
        """Lazy-loads local Whisper model."""
        if not self._local_model_loaded:
            device = "cuda" if torch.cuda.is_available() else "cpu"
            logger.info(f"Loading local Whisper model ({settings.WHISPER_MODEL_SIZE}) on: {device}")
            try:
                self._model = whisper.load_model(settings.WHISPER_MODEL_SIZE, device=device)
                self._local_model_loaded = True
            except Exception as e:
                logger.error(f"Failed to load local Whisper model: {e}")
                raise RuntimeError(f"Failed to load local Whisper model: {e}")

    async def transcribe(self, audio_path: str) -> Dict[str, Any]:
        """
        Transcribes the given audio file using Groq -> OpenAI -> Local fallback chain.
        """
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        logger.info(f"Processing: {audio_path}")

        # Groq
        if self.groq_client:
            try:
                logger.info("Transcribing via Groq...")
                return await self._call_whisper_api(self.groq_client, audio_path, "whisper-large-v3")
            except Exception as e:
                logger.warning(f"Groq failed: {e}. Falling back...")

        # OpenAI
        if self.openai_client:
            try:
                logger.info("Transcribing via OpenAI...")
                return await self._call_whisper_api(self.openai_client, audio_path, "whisper-1")
            except Exception as e:
                logger.warning(f"OpenAI failed: {e}. Falling back...")

        # Local
        logger.info("Transcribing via Local Whisper...")
        return self._transcribe_local(audio_path)

    async def _call_whisper_api(self, client: AsyncOpenAI, audio_path: str, model: str) -> Dict[str, Any]:
        """Calls Whisper API for transcription."""
        with open(audio_path, "rb") as f:
            transcript = await client.audio.transcriptions.create(
                model=model,
                file=f,
                response_format="verbose_json",
                timestamp_granularities=["segment"]
            )

        segments = []
        if hasattr(transcript, 'segments'):
            for seg in transcript.segments:
                segments.append({
                    "start": seg.start,
                    "end": seg.end,
                    "text": seg.text.strip()
                })

        return {"text": transcript.text, "segments": segments}

    def _transcribe_local(self, audio_path: str) -> Dict[str, Any]:
        """Transcribes using local Whisper."""
        self._ensure_local_model()
        # Using standard transcription
        result = self._model.transcribe(audio_path, fp16=False)

        segments = []
        for seg in result.get("segments", []):
            segments.append({
                "start": seg["start"],
                "end": seg["end"],
                "text": seg["text"].strip()
            })

        return {"text": result.get("text", ""), "segments": segments}
