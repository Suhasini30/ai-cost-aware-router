from pydantic_settings import BaseSettings, SettingsConfigDict


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

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()