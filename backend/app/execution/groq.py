"""Groq adapter (OpenAI-compatible chat API)."""

from app.execution.openai_compat import OpenAICompatibleAdapter


class GroqAdapter(OpenAICompatibleAdapter):
    provider = "groq"
    base_url = "https://api.groq.com/openai/v1"
