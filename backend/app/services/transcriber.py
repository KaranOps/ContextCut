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
    Transcription service respecting the configured provider (OpenAI / Groq / Local).
    Supports 'gpt-4o-transcribe', 'whisper-1', etc.
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
        """Initializes API client based on settings."""
        self.client = None
        self.provider = settings.TRANSCRIPTION_PROVIDER
        self.model_name = settings.TRANSCRIPTION_MODEL
        
        logger.info(f"Initializing Transcriber. Provider: {self.provider}, Model: {self.model_name}")

        if self.provider == "openai" and settings.OPENAI_API_KEY:
            self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        elif self.provider == "groq" and settings.GROQ_API_KEY:
            self.client = AsyncOpenAI(
                base_url="https://api.groq.com/openai/v1",
                api_key=settings.GROQ_API_KEY
            )
        
    async def transcribe(self, audio_path: str) -> Dict[str, Any]:
        """
        Transcribes the audio file using the configured provider.
        """
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
            
        logger.info(f"Processing transcription request for: {audio_path}")

        # 1. Direct Local
        if self.provider == "local":
            return self._transcribe_local(audio_path)
        
        # 2. API (OpenAI / Groq)
        if self.client:
            try:
                return await self._call_whisper_api(audio_path)
            except Exception as e:
                logger.error(f"{self.provider} transcription failed: {e}. Falling back to LOCAL.")
                # Fallback to local
                return self._transcribe_local(audio_path)
        
        # 3. Fallback if client didn't initialize
        logger.warning("Transcriber configured for API but client not ready. Falling back to LOCAL.")
        return self._transcribe_local(audio_path)

    async def _call_whisper_api(self, audio_path: str) -> Dict[str, Any]:
        """
        Calls the configured API for transcription.
        """
        logger.info(f"Transcribing via {self.provider} model='{self.model_name}'...")
        
        request_params = {
            "model": self.model_name,
            "temperature": 0.0, # Improve stability and segmentation
        }

        # Model-Specific Configuration
        if "gpt" in self.model_name.lower() and "whisper" not in self.model_name.lower():
             # GPT-4o Audio (Text-Only)
             request_params["response_format"] = "json"
        else:
            # Whisper / Default (Timestamps)
            request_params["response_format"] = "verbose_json"
            request_params["timestamp_granularities"] = ["segment"]

        try:
            with open(audio_path, "rb") as f:
                transcript = await self.client.audio.transcriptions.create(
                    file=f,
                    **request_params
                )
        except Exception as e:
            logger.error(f"API Request Failed for params {request_params}: {e}")
            raise e

        # Parse Response
        segments = []
        full_text = ""

        if request_params["response_format"] == "verbose_json":
             if hasattr(transcript, 'segments'):
                for seg in transcript.segments:
                    segments.append({
                        "start": seg.start,
                        "end": seg.end,
                        "text": seg.text.strip()
                    })
             full_text = getattr(transcript, 'text', "")
             
        else:
             # Text-Only Response
             full_text = getattr(transcript, 'text', "")
             segments.append({
                 "start": 0.0,
                 "end": 0.0,
                 "text": full_text.strip()
             })

        # Final Fallback
        if not segments and full_text:
             segments.append({"start": 0.0, "end": 0.0, "text": full_text})

        return {"text": full_text, "segments": segments}

    def _transcribe_local(self, audio_path: str) -> Dict[str, Any]:
        """Transcribes using local Whisper model."""
        self._ensure_local_model()
        
        local_model_size = settings.WHISPER_MODEL_SIZE
        logger.info(f"Transcribing via Local Whisper ({local_model_size})...")
        
        # Use standard transcription
        result = self._model.transcribe(audio_path, fp16=False)

        segments = []
        for seg in result.get("segments", []):
            segments.append({
                "start": seg["start"],
                "end": seg["end"],
                "text": seg["text"].strip()
            })

        return {"text": result.get("text", ""), "segments": segments}

    def _ensure_local_model(self):
        """Lazy-loads local Whisper model."""
        if not self._local_model_loaded:
            device = "cuda" if torch.cuda.is_available() else "cpu"
            model_size = settings.WHISPER_MODEL_SIZE
            logger.info(f"Loading local Whisper model ({model_size}) on: {device}")
            try:
                self._model = whisper.load_model(model_size, device=device)
                self._local_model_loaded = True
            except Exception as e:
                logger.error(f"Failed to load local Whisper model: {e}")
                raise RuntimeError(f"Failed to load local Whisper model: {e}")
