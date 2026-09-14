"""LangSmith tracing setup.

KEY SEMANTICS (do not mix):
- `settings.langchain_api_key` is the LANGSMITH key → observability only.
- Provider keys (`mistral_api_key`, `gemini_api_key`, ...) are for inference.
- The classifier agent must NEVER receive the LangSmith key.
"""

import os

from app.core.config import Settings


def setup_tracing(app_settings: Settings) -> bool:
    """Enable LangSmith tracing if credentials are present.

    The LangSmith SDK reads `LANGCHAIN_*` env vars, not our Settings
    object, so we mirror them here. Returns True when tracing is active.
    Safe no-op when no key is configured (dev/tests work offline).
    """
    key = app_settings.langchain_api_key
    if not key:
        return False
    os.environ["LANGCHAIN_TRACING_V2"] = (
        "true" if app_settings.langchain_tracing_v2 else "false"
    )
    os.environ["LANGCHAIN_API_KEY"] = key
    os.environ["LANGCHAIN_PROJECT"] = app_settings.langchain_project
    return bool(key and app_settings.langchain_tracing_v2)
