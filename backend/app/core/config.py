import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "ContextCut"
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    DATA_DIR: str = os.getenv("DATA_DIR", "../../data")
    WHISPER_MODEL_SIZE: str = os.getenv("WHISPER_MODEL_SIZE", "turbo")

    class Config:
        case_sensitive = True

settings = Settings()
