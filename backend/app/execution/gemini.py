"""Gemini adapter (moved from the router agent — behavior preserved)."""

import time

import httpx

from app.execution.base import ExecutionResult, ProviderAdapter


class GeminiAdapter(ProviderAdapter):
    provider = "gemini"

    def execute(
        self,
        *,
        model_api_id: str,
        prompt: str,
        system_prompt: str | None = None,
        json_mode: bool = False,
    ) -> ExecutionResult:
        body: dict = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0,
                "maxOutputTokens": self.max_tokens,
            },
        }
        if system_prompt:
            body["system_instruction"] = {"parts": [{"text": system_prompt}]}
        if json_mode:
            body["generationConfig"]["responseMimeType"] = "application/json"

        started = time.perf_counter()
        with httpx.Client(timeout=self.timeout_s) as client:
            resp = client.post(
                "https://generativelanguage.googleapis.com/v1beta/models/"
                f"{model_api_id}:generateContent",
                headers={"x-goog-api-key": self.api_key},
                json=body,
            )
            resp.raise_for_status()
            data = resp.json()
        latency_ms = (time.perf_counter() - started) * 1000.0

        text = data["candidates"][0]["content"]["parts"][0]["text"]
        usage = data.get("usageMetadata") or {}
        return ExecutionResult(
            text=text,
            provider=self.provider,
            model_api_id=model_api_id,
            latency_ms=latency_ms,
            input_tokens=usage.get("promptTokenCount"),
            output_tokens=usage.get("candidatesTokenCount"),
            total_tokens=usage.get("totalTokenCount"),
        )
