"""
Configuration management for AutoShorts backend.
Loads environment variables and provides provider switching logic.
"""
from pydantic_settings import BaseSettings
from typing import Literal
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)


class Settings(BaseSettings):
    # Common
    ENV: str = "dev"
    LOG_LEVEL: str = "INFO"

    # Backend network
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8080
    FRONTEND_ORIGIN: str = "http://localhost:5173"

    # Redis / Celery
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"

    # ComfyUI
    COMFY_URL: str = "http://localhost:8188"
    COMFY_WS: str = "ws://localhost:8188/ws"
    COMFY_WORKFLOW: str = "backend/app/providers/images/workflows/flux_omni_lora.json"

    # Provider switches
    IMAGE_PROVIDER: Literal["comfyui", "gemini"] = "gemini"
    TTS_PROVIDER: Literal["elevenlabs", "playht"] = "elevenlabs"
    MUSIC_PROVIDER: Literal["elevenlabs", "mubert", "udio", "suno"] = "elevenlabs"

    # Model/Prompt settings
    ART_STYLE_LORA: str = "WatercolorDream_v2"
    BASE_CHAR_SEED: int = 1001
    BG_SEED_BASE: int = 2000

    # External API keys
    OPENAI_API_KEY: str = ""
    ELEVENLABS_API_KEY: str = ""
    PLAYHT_API_KEY: str = ""
    PLAYHT_USER_ID: str = ""
    MUBERT_LICENSE: str = ""
    UDIO_API_KEY: str = ""

    # Gemini (Image Generation - Nano Banana)
    GEMINI_API_KEY: str = ""

    # S3/R2 Storage (optional)
    S3_ENDPOINT: str = ""
    S3_ACCESS_KEY: str = ""
    S3_SECRET_KEY: str = ""
    S3_BUCKET: str = ""

    class Config:
        # Look for .env in current dir, parent dir, or grandparent dir
        env_file = str(Path(__file__).resolve().parent.parent.parent / ".env")
        case_sensitive = True


# Singleton instance
settings = Settings()


def get_settings() -> Settings:
    """Dependency injection helper for FastAPI."""
    return settings
