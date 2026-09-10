"""xAI adapter (Grok — OpenAI-compatible chat API)."""

from app.execution.openai_compat import OpenAICompatibleAdapter


class XaiAdapter(OpenAICompatibleAdapter):
    provider = "xai"
    base_url = "https://api.x.ai/v1"
