import json
import logging
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI
from app.core.config import settings

logger = logging.getLogger(__name__)

class TranslationService:
    """
    Service to conditionally translate transcribed segments to English.
    Prioritizes cost optimization by skipping translation if speech is already English.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TranslationService, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        self.client = None
        self.provider = settings.TRANSLATION_PROVIDER
        self.model = settings.TRANSLATION_MODEL

        logger.info(f"Initializing TranslationService with Provider: {self.provider}, Model: {self.model}")

        if self.provider == "openai" and settings.OPENAI_API_KEY:
            self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        elif self.provider == "groq" and settings.GROQ_API_KEY:
            self.client = AsyncOpenAI(
                base_url="https://api.groq.com/openai/v1",
                api_key=settings.GROQ_API_KEY
            )
        elif self.provider == "local":
            logger.info("Local translation provider selected. Note: Local LLM translation not fully implemented, passing through text.")
        else:
            logger.warning("No valid translation provider configured.")

    async def translate_if_needed(self, segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Translates segments to English if they are not already English.
        """
        if not segments:
            return []

        # 1. Detect Language
        # Sample first few segments for speed (approx first 1000 chars)
        sample_text = " ".join([s.get("text", "") for s in segments[:10]])[:1000]
        is_english = await self._is_english(sample_text)

        if is_english:
            logger.info("English detected; skipping translation.")
            return segments

        # 2. Translate if not English
        if not self.client:
             logger.warning("Non-English detected but no Translation Client available. Returning original.")
             return segments

        logger.info(f"Non-English detected. Translating using {self.provider} ({self.model})...")
        return await self._translate_segments(segments)

    async def _is_english(self, text: str) -> bool:
        """
        Determines if the text is English using a lightweight check or LLM.
        """
        # Attempt to use langdetect if installed
        try:
            from langdetect import detect
            try:
                # langdetect is fast and effective for this
                lang = detect(text)
                return lang == 'en'
            except Exception:
                pass 
        except ImportError:
            pass

        # Fallback to LLM if client available
        if self.client:
            try:
                # Use a lightweight check prompt
                response = await self.client.chat.completions.create(
                    model=self.model, 
                    messages=[
                        {"role": "system", "content": "You are a language detector. Reply with 'TRUE' if the text is English, 'FALSE' otherwise. Do not explain."},
                        {"role": "user", "content": f"Text: {text}"}
                    ],
                    temperature=0.0,
                    max_tokens=10
                )
                content = response.choices[0].message.content.strip().upper()
                return "TRUE" in content
            except Exception as e:
                logger.warning(f"Language detection failed: {e}. Assuming English to avoid unnecessary translation costs if unsure.")
                return True # Default to English if detection fails to save costs/time? Or False? 
                # If we assume English, we skip translation. If it's effectively meaningless, skipping is fine.
        
        return True # Default if no other means

    async def _translate_segments(self, segments: List[Dict]) -> List[Dict]:
        """
        Translates list of segments preserving structure.
        """
        system_prompt = (
            "You are a translation expert. I will provide a list of JSON segments with 'start', 'end', and 'text'.\n"
            "Translate the 'text' to English.\n"
            "CRITICAL: Return a JSON object with a single key 'segments' containing the list of translated segments.\n"
            "Preserve 'start' and 'end' values exactly. Do not merge or split segments."
        )

        user_content = json.dumps(segments, ensure_ascii=False)

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            parsed = json.loads(content)
            return parsed.get("segments", [])
            
        except Exception as e:
            logger.error(f"Translation failed: {e}")
            return segments # Return original on failure
