import json

import httpx
import pytest

from app.core.config import Settings
from app.execution import (
    GeminiAdapter,
    GroqAdapter,
    MistralAdapter,
    XaiAdapter,
    execute,
    execute_json,
    get_adapter,
)
from app.execution import service as service_module


def _settings(**overrides):
    base = dict(
        mistral_api_key="m-key",
        gemini_api_key="g-key",
        xai_api_key="x-key",
        groq_api_key="q-key",
        execution_timeout_s=5.0,
        execution_max_tokens=64,
    )
    base.update(overrides)
    return Settings(**base)


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


def _fake_client_class(response, capture):
    class _FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def post(self, url, headers=None, json=None):
            capture["url"] = url
            capture["headers"] = headers or {}
            capture["json"] = json or {}
            return _FakeResponse(response)

    return _FakeClient


def _patch_client(monkeypatch, module_path, response, capture):
    monkeypatch.setattr(
        module_path, _fake_client_class(response, capture)
    )


# --- Mistral ---


def test_mistral_request_shape_and_parsing(monkeypatch):
    capture = {}
    _patch_client(
        monkeypatch,
        "app.execution.mistral.httpx.Client",
        {
            "choices": [{"message": {"content": '{"a": 1}'}}],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 5,
                "total_tokens": 15,
            },
        },
        capture,
    )
    adapter = MistralAdapter(api_key="m-key", timeout_s=5.0, max_tokens=64)
    result = adapter.execute(
        model_api_id="mistral-large-latest",
        prompt="hi",
        system_prompt="sys",
        json_mode=True,
    )
    assert capture["url"] == "https://api.mistral.ai/v1/chat/completions"
    assert capture["headers"] == {"Authorization": "Bearer m-key"}
    assert capture["json"]["model"] == "mistral-large-latest"
    assert capture["json"]["messages"] == [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "hi"},
    ]
    assert capture["json"]["response_format"] == {"type": "json_object"}
    assert result.text == '{"a": 1}'
    assert (result.input_tokens, result.output_tokens, result.total_tokens) == (10, 5, 15)
    assert result.provider == "mistral"


def test_mistral_no_system_no_json_mode(monkeypatch):
    capture = {}
    _patch_client(
        monkeypatch,
        "app.execution.mistral.httpx.Client",
        {"choices": [{"message": {"content": "hello"}}]},
        capture,
    )
    result = MistralAdapter(api_key="k").execute(
        model_api_id="m", prompt="hi"
    )
    assert capture["json"]["messages"] == [{"role": "user", "content": "hi"}]
    assert "response_format" not in capture["json"]
    assert result.total_tokens is None


# --- Gemini ---


def test_gemini_request_shape_and_parsing(monkeypatch):
    capture = {}
    _patch_client(
        monkeypatch,
        "app.execution.gemini.httpx.Client",
        {
            "candidates": [{'content': {'parts': [{'text': '{"a": 1}'}]}}],
            "usageMetadata": {
                "promptTokenCount": 7,
                "candidatesTokenCount": 3,
                "totalTokenCount": 10,
            },
        },
        capture,
    )
    adapter = GeminiAdapter(api_key="g-key", timeout_s=5.0, max_tokens=64)
    result = adapter.execute(
        model_api_id="gemini-1.5-flash",
        prompt="hi",
        system_prompt="sys",
        json_mode=True,
    )
    assert capture["url"] == (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        "gemini-1.5-flash:generateContent"
    )
    assert capture["headers"] == {"x-goog-api-key": "g-key"}
    assert capture["json"]["generationConfig"]["responseMimeType"] == "application/json"
    assert result.text == '{"a": 1}'
    assert (result.input_tokens, result.output_tokens, result.total_tokens) == (7, 3, 10)


# --- xAI / Groq (shared OpenAI-compatible base) ---


def test_xai_url_and_auth(monkeypatch):
    capture = {}
    _patch_client(
        monkeypatch,
        "app.execution.openai_compat.httpx.Client",
        {
            "choices": [{"message": {"content": "yo"}}],
            "usage": {"prompt_tokens": 4, "completion_tokens": 2, "total_tokens": 6},
        },
        capture,
    )
    result = XaiAdapter(api_key="x-key").execute(
        model_api_id="grok-3", prompt="hi", system_prompt="sys"
    )
    assert capture["url"] == "https://api.x.ai/v1/chat/completions"
    assert capture["headers"] == {"Authorization": "Bearer x-key"}
    assert capture["json"]["model"] == "grok-3"
    assert result.total_tokens == 6


def test_groq_url_and_auth(monkeypatch):
    capture = {}
    _patch_client(
        monkeypatch,
        "app.execution.openai_compat.httpx.Client",
        {"choices": [{"message": {"content": "yo"}}]},
        capture,
    )
    GroqAdapter(api_key="q-key").execute(model_api_id="llama-3", prompt="hi")
    assert capture["url"] == "https://api.groq.com/openai/v1/chat/completions"
    assert capture["headers"] == {"Authorization": "Bearer q-key"}


# --- Base / factory ---


def test_adapter_rejects_missing_key():
    with pytest.raises(ValueError, match="Missing API key"):
        MistralAdapter(api_key="")


def test_factory_resolves_all_four():
    cfg = _settings()
    assert isinstance(get_adapter("mistral", cfg), MistralAdapter)
    assert isinstance(get_adapter("gemini", cfg), GeminiAdapter)
    assert isinstance(get_adapter("xai", cfg), XaiAdapter)
    assert isinstance(get_adapter("groq", cfg), GroqAdapter)
    assert get_adapter("MISTRAL", cfg).provider == "mistral"


def test_factory_unknown_provider():
    with pytest.raises(ValueError, match="Unknown provider"):
        get_adapter("nope", _settings())


def test_factory_missing_key():
    with pytest.raises(ValueError, match="Missing API key"):
        get_adapter("groq", _settings(groq_api_key=None))


def test_factory_applies_execution_settings():
    adapter = get_adapter("mistral", _settings())
    assert adapter.timeout_s == 5.0
    assert adapter.max_tokens == 64


# --- Service ---


def test_service_max_tokens_override(monkeypatch):
    captured = {}

    class _Stub:
        max_tokens = 64

        def execute(self, **kwargs):
            captured["max_tokens"] = self.max_tokens
            from app.execution.base import ExecutionResult

            return ExecutionResult(
                text="{}",
                provider="x",
                model_api_id="m",
                latency_ms=1.0,
            )

    stub = _Stub()
    monkeypatch.setattr(
        service_module, "get_adapter", lambda provider, cfg: stub
    )
    execute(
        provider="mistral",
        model_api_id="m",
        prompt="hi",
        max_tokens=11,
        app_settings=_settings(),
    )
    assert captured["max_tokens"] == 11


def test_execute_json_parses(monkeypatch):
    from app.execution.base import ExecutionResult

    monkeypatch.setattr(
        service_module,
        "get_adapter",
        lambda provider, cfg: type(
            "_S",
            (),
            {
                "execute": lambda self, **k: ExecutionResult(
                    text='{"a": 1}',
                    provider="m",
                    model_api_id="m",
                    latency_ms=1.0,
                )
            },
        )(),
    )
    payload, result = execute_json(
        provider="mistral", model_api_id="m", prompt="hi",
        app_settings=_settings(),
    )
    assert payload == {"a": 1}
    assert result.provider == "m"


def test_execute_json_bad_json_raises(monkeypatch):
    from app.execution.base import ExecutionResult

    monkeypatch.setattr(
        service_module,
        "get_adapter",
        lambda provider, cfg: type(
            "_S",
            (),
            {
                "execute": lambda self, **k: ExecutionResult(
                    text="not json",
                    provider="m",
                    model_api_id="m",
                    latency_ms=1.0,
                )
            },
        )(),
    )
    with pytest.raises(json.JSONDecodeError):
        execute_json(
            provider="mistral", model_api_id="m", prompt="hi",
            app_settings=_settings(),
        )


def test_transport_errors_propagate(monkeypatch):
    class _BoomClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def post(self, *args, **kwargs):
            raise httpx.ConnectError("down")

    monkeypatch.setattr("app.execution.mistral.httpx.Client", _BoomClient)
    with pytest.raises(httpx.ConnectError):
        MistralAdapter(api_key="k").execute(model_api_id="m", prompt="hi")
