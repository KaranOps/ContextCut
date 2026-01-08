import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "ContextCut"
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    DATA_DIR: str = os.getenv("DATA_DIR", "../../data")
    WHISPER_MODEL_SIZE: str = os.getenv("WHISPER_MODEL_SIZE", "small")
    VISION_FRAME_INTERVAL: int = int(os.getenv("VISION_FRAME_INTERVAL", "2"))
    
    # SemanticSync / Editing Constraints
    MIN_BROLL_DURATION: float = float(os.getenv("MIN_BROLL_DURATION", "1.5"))
    BROLL_COOL_DOWN_SECONDS: float = float(os.getenv("BROLL_COOL_DOWN_SECONDS", "5.0"))
    BROLL_DIVERSITY_WINDOW_SECONDS: float = float(os.getenv("BROLL_DIVERSITY_WINDOW_SECONDS", "14.0"))
    MIN_LLM_CONFIDENCE: float = float(os.getenv("MIN_LLM_CONFIDENCE", "0.6"))

    # Vector Service / Model Switching
    EMBEDDING_PROVIDER: str = os.getenv("EMBEDDING_PROVIDER", "local")  # "local" or "openai"
    LOCAL_MODEL_NAME: str = os.getenv("LOCAL_MODEL_NAME", "nomic-ai/nomic-embed-text-v1.5")
    VECTOR_TOP_K: int = int(os.getenv("VECTOR_TOP_K", "5"))
    SIMILARITY_THRESHOLD: float = float(os.getenv("SIMILARITY_THRESHOLD", "0.3"))
    CHROMA_DB_PATH: str = os.getenv("CHROMA_DB_PATH", "./chroma_db")
    COLLECTION_NAME_PREFIX: str = os.getenv("COLLECTION_NAME_PREFIX", "semanticsync_catalog")

    class Config:
        case_sensitive = True

settings = Settings()
