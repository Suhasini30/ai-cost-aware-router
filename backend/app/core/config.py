from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve backend/.env regardless of CWD (uvicorn, pytest, etc.)
_BACKEND_DIR = Path(__file__).resolve().parents[2]
_ENV_FILE = _BACKEND_DIR / ".env"


class Settings(BaseSettings):
    app_name: str = "Cost-Aware Multi-Model Router"
    app_version: str = "1.0.0"
    debug: bool = True
    environment: str = "development"

    mistral_api_key: str | None = None
    gemini_api_key: str | None = None
    xai_api_key: str | None = None
    groq_api_key: str | None = None
    deepseek_api_key: str | None = None

    langchain_tracing_v2: bool = True
    langchain_api_key: str | None = None
    langchain_project: str = "cost-aware-router"

    confidence_threshold: float = Field(default=0.75, ge=0.0, le=1.0)

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()