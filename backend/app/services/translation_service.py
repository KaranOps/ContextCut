import json
import logging
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI
from app.core.config import settings

logger = logging.getLogger(__name__)

class TranslationService:
    """
    Service to translate transcribed segments to English using High-Performance LLMs (Groq > OpenAI).
    Strictly preserves time-codes and JSON structure.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TranslationService, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """Initializes API clients."""
        self.groq_client = None
        self.openai_client = None

        if settings.GROQ_API_KEY:
            logger.info("Initializing Groq Client for Translation.")
            self.groq_client = AsyncOpenAI(
                base_url="https://api.groq.com/openai/v1",
                api_key=settings.GROQ_API_KEY
            )

        if settings.OPENAI_API_KEY:
            logger.info("Initializing OpenAI Client for Translation.")
            self.openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    async def translate_segments(self, segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Translates a list of segments to English.
        Input format: [{"start": 0.0, "end": 2.0, "text": "Original Text"}]
        Output format: [{"start": 0.0, "end": 2.0, "text": "Translated Text"}]
        """
        if not segments:
            return []

        # Groq
        if self.groq_client:
            try:
                return await self._translate_with_llm(self.groq_client, segments, "openai/gpt-oss-120b")
            except Exception as e:
                logger.warning(f"Groq translation failed: {e}. Falling back...")

        # OpenAI
        if self.openai_client:
            try:
                return await self._translate_with_llm(self.openai_client, segments, "gpt-4-turbo")
            except Exception as e:
                logger.error(f"OpenAI translation failed: {e}")

        raise RuntimeError("Translation failed: No available LLM clients or all attempts failed.")

    async def _translate_with_llm(self, client: AsyncOpenAI, segments: List[Dict], model: str) -> List[Dict]:
        """
        Internal method to call LLM and parse response.
        """
        system_prompt = (
            "You are a translation expert. I will provide a list of JSON segments with 'start', 'end', and 'text' in a native language.\n"
            "Translate the 'text' to English.\n"
            "CRITICAL: You must return the exact same JSON structure with the same 'start' and 'end' values. Do not merge or split segments.\n"
            "Only return valid JSON. Do not include markdown formatting (like ```json), just the raw JSON string."
        )

        user_content = json.dumps(segments, ensure_ascii=False)

        try:
            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ],
                temperature=0.1, 
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content            
            return await self._translate_with_wrapper(client, segments, model)

        except Exception as e:
            raise e

    async def _translate_with_wrapper(self, client: AsyncOpenAI, segments: List[Dict], model: str) -> List[Dict]:
        system_prompt = (
            "You are a translation expert. I will provide a list of JSON segments with 'start', 'end', and 'text' in a native language.\n"
            "Translate the 'text' to English.\n"
            "CRITICAL: Return a JSON object with a single key 'segments' containing the list of translated segments.\n"
            "Preserve 'start' and 'end' values exactly. Do not merge or split segments."
        )
        
        user_content = json.dumps(segments, ensure_ascii=False)

        response = await client.chat.completions.create(
            model=model,
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
