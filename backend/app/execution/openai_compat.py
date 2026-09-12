"""Shared base for OpenAI-compatible chat APIs (currently Groq)."""

import time

import httpx

from app.execution.base import ExecutionResult, ProviderAdapter


class OpenAICompatibleAdapter(ProviderAdapter):
    """POST {base_url}/chat/completions with the OpenAI request shape."""

    base_url: str = ""

    def execute(
        self,
        *,
        model_api_id: str,
        prompt: str,
        system_prompt: str | None = None,
        json_mode: bool = False,
    ) -> ExecutionResult:
        messages: list[dict] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        body: dict = {
            "model": model_api_id,
            "messages": messages,
            "temperature": 0,
            "max_tokens": self.max_tokens,
        }
        if json_mode:
            body["response_format"] = {"type": "json_object"}

        started = time.perf_counter()
        with httpx.Client(timeout=self.timeout_s) as client:
            resp = client.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=body,
            )
            resp.raise_for_status()
            data = resp.json()
        latency_ms = (time.perf_counter() - started) * 1000.0

        message = data["choices"][0]["message"]
        usage = data.get("usage") or {}
        return ExecutionResult(
            text=message.get("content") or "",
            provider=self.provider,
            model_api_id=model_api_id,
            latency_ms=latency_ms,
            input_tokens=usage.get("prompt_tokens"),
            output_tokens=usage.get("completion_tokens"),
            total_tokens=usage.get("total_tokens"),
        )
