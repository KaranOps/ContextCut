import os
from typing import Literal, Optional
from pydantic_settings import BaseSettings

ProviderType = Literal["openai", "groq", "local"]

class Settings(BaseSettings):
    PROJECT_NAME: str = "ContextCut"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Path Configuration
    # We resolve absolute paths to ensure consistency regardless of CWD.
    # config.py is in backend/app/core/ => 3 levels up to backend => 4 levels up to root
    BACKEND_DIR: str = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    PROJECT_ROOT: str = os.path.dirname(BACKEND_DIR)
    
    DATA_DIR: str = os.getenv("DATA_DIR", os.path.join(PROJECT_ROOT, "data"))
    CHROMA_DB_PATH: str = os.getenv("CHROMA_DB_PATH", os.path.join(DATA_DIR, "chroma_db"))

    # API Keys
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    
    # Cloud / Database Keys
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")
    SUPABASE_DB_URL: str = os.getenv("SUPABASE_DB_URL", "") # connection string
    CLOUDINARY_URL: str = os.getenv("CLOUDINARY_URL", "")
    
    # Storage Configuration
    STORAGE_PROVIDER: Literal["local", "supabase"] = os.getenv("STORAGE_PROVIDER", "supabase")
    TEMP_DIR: str = os.getenv("TEMP_DIR", os.path.join(DATA_DIR, "temp_processing"))

    # Default Global Provider (derived or explicit)
    # The individual providers below will default to this if not set
    
    # --- Granular Service Configuration ---
    
    # Transcription
    TRANSCRIPTION_PROVIDER: Optional[ProviderType] = None 
    TRANSCRIPTION_MODEL: Optional[str] = None
    WHISPER_MODEL_SIZE: str = os.getenv("WHISPER_MODEL_SIZE", "small") 
    
    # Translation
    TRANSLATION_PROVIDER: Optional[ProviderType] = None
    TRANSLATION_MODEL: Optional[str] = None
    
    # Vision
    VISION_PROVIDER: Optional[ProviderType] = None
    VISION_MODEL: Optional[str] = None
    VISION_FRAME_INTERVAL: int = int(os.getenv("VISION_FRAME_INTERVAL", "2"))
    
    # Embedding / Search
    EMBEDDING_PROVIDER: Optional[ProviderType] = None
    EMBEDDING_MODEL: Optional[str] = None

    
    LOCAL_MODEL_NAME: str = os.getenv("LOCAL_MODEL_NAME", "nomic-ai/nomic-embed-text-v1.5") # Legacy ref

    # Director / Timeline
    DIRECTOR_PROVIDER: Optional[ProviderType] = None
    DIRECTOR_MODEL: Optional[str] = None
    
    # SemanticSync / Editing Constraints
    MIN_BROLL_DURATION: float = float(os.getenv("MIN_BROLL_DURATION", "1.5"))
    BROLL_COOL_DOWN_SECONDS: float = float(os.getenv("BROLL_COOL_DOWN_SECONDS", "5.0"))
    BROLL_DIVERSITY_WINDOW_SECONDS: float = float(os.getenv("BROLL_DIVERSITY_WINDOW_SECONDS", "14.0"))
    MIN_LLM_CONFIDENCE: float = float(os.getenv("MIN_LLM_CONFIDENCE", "0.4"))
    
    VECTOR_TOP_K: int = int(os.getenv("VECTOR_TOP_K", "5"))
    SIMILARITY_THRESHOLD: float = float(os.getenv("SIMILARITY_THRESHOLD", "0.3"))
    # CHROMA_DB_PATH is now defined above to ensure it depends on DATA_DIR
    COLLECTION_NAME_PREFIX: str = os.getenv("COLLECTION_NAME_PREFIX", "semanticsync_catalog")

    class Config:
        case_sensitive = True
        env_file = ".env"

    def __init__(self, **data):
        super().__init__(**data)
        self._configure_defaults()

    def _configure_defaults(self):
        """
        Configures defaults based on available API keys and hierarchy:
        OpenAI (Priority) -> Groq -> Local.
        """
        # 1. Determine Global Primary Provider if not specific overrides
        primary_provider: ProviderType = "local"
        if self.OPENAI_API_KEY:
            primary_provider = "openai"
        elif self.GROQ_API_KEY:
            primary_provider = "groq"
            
        # Use Groq for Transcription if available (Speed + Granularity)
        transcription_priority_provider = primary_provider
        if self.GROQ_API_KEY:
            transcription_priority_provider = "groq"
            
        # 2. Defaults Map
        defaults = {
            "openai": {
                "transcription_model": "whisper-1",
                "translation_model": "gpt-4o",
                "vision_model": "gpt-4o-mini",
                "embedding_model": "text-embedding-ada-002",
                "director_model": "o3",
            },
            "groq": {
                "transcription_model": "whisper-large-v3",
                "translation_model": "llama3-70b-8192", 
                "vision_model": "llama-3.2-11b-vision-preview",
                "embedding_model": "local", 
                "director_model": "llama-3.3-70b-versatile",
            },
            "local": {
                "transcription_model": self.WHISPER_MODEL_SIZE,
                "translation_model": "local",
                "vision_model": "local",
                "embedding_model": self.LOCAL_MODEL_NAME,
                "director_model": "local",
            }
        }

        # Helper to set provider and model
        def set_provider_config(field_provider, field_model, key_prefix, forced_default_provider=None):
            # Resolve Provider
            provider = getattr(self, field_provider)
            if provider is None:
                provider = forced_default_provider if forced_default_provider else primary_provider
                setattr(self, field_provider, provider)
            
            # Resolve Model
            model = getattr(self, field_model)
            if model is None:
                # Use default for the chosen provider
                default_models = defaults.get(provider, defaults["local"])
                # Handle edge case where Groq might default to local embedding
                target_model = default_models.get(f"{key_prefix}_model", "local")
                
                # If falling back to local for a specific service (like embeddings in Groq), 
                # we might need to adjust the provider? 
                # For now, we just set the model.
                setattr(self, field_model, target_model)

        # Apply to all services
        set_provider_config("TRANSCRIPTION_PROVIDER", "TRANSCRIPTION_MODEL", "transcription", forced_default_provider=transcription_priority_provider)
        set_provider_config("TRANSLATION_PROVIDER", "TRANSLATION_MODEL", "translation")
        set_provider_config("VISION_PROVIDER", "VISION_MODEL", "vision")
        set_provider_config("EMBEDDING_PROVIDER", "EMBEDDING_MODEL", "embedding")
        set_provider_config("DIRECTOR_PROVIDER", "DIRECTOR_MODEL", "director")

settings = Settings()
