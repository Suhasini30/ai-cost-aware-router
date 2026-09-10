"""Provider factory — the only place that maps names to adapters."""

from app.core.config import Settings
from app.execution.base import ProviderAdapter
from app.execution.gemini import GeminiAdapter
from app.execution.groq import GroqAdapter
from app.execution.mistral import MistralAdapter
from app.execution.xai import XaiAdapter


def get_adapter(provider: str, app_settings: Settings) -> ProviderAdapter:
    """Resolve a provider name to a configured adapter.

    Raises:
        ValueError: unknown provider or missing provider API key.
    """
    key = (provider or "").lower()
    timeout_s = app_settings.execution_timeout_s
    max_tokens = app_settings.execution_max_tokens
    if key == "mistral":
        api_key = app_settings.mistral_api_key
        cls = MistralAdapter
    elif key == "gemini":
        api_key = app_settings.gemini_api_key
        cls = GeminiAdapter
    elif key == "xai":
        api_key = app_settings.xai_api_key
        cls = XaiAdapter
    elif key == "groq":
        api_key = app_settings.groq_api_key
        cls = GroqAdapter
    else:
        raise ValueError(f"Unknown provider: {provider!r}")
    if not api_key:
        raise ValueError(f"Missing API key for provider {key!r}")
    return cls(api_key=api_key, timeout_s=timeout_s, max_tokens=max_tokens)
