import os
import importlib

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import Settings, settings
from app.core.tracing import setup_tracing
from app.main import app
from app.router.agent import (
    FALLBACK_MODEL,
    classify_prompt,
    fallback_classify,
)
from app.router.schemas import RouterDecision

client = TestClient(app)


def _offline_settings(**overrides):
    """Settings with no provider/LangSmith keys (forces fallback path)."""
    base = dict(
        mistral_api_key=None,
        gemini_api_key=None,
        langchain_api_key=None,
        classifier_model="mistral-large-latest",
        classifier_provider="mistral",
    )
    base.update(overrides)
    return Settings(**base)


# --- Schema ---


def test_router_decision_valid():
    d = RouterDecision(
        task_type="coding",
        complexity="high",
        capability="coding",
        quality_required="high",
        confidence=0.9,
        reason="Contains code keywords.",
    )
    assert d.confidence == 0.9


def test_router_decision_rejects_bad_enum():
    with pytest.raises(ValidationError):
        RouterDecision(
            task_type="banana",
            complexity="low",
            capability="text",
            quality_required="standard",
            confidence=0.5,
            reason="bad",
        )


def test_router_decision_rejects_bad_confidence():
    with pytest.raises(ValidationError):
        RouterDecision(
            task_type="math",
            complexity="low",
            capability="reasoning",
            quality_required="standard",
            confidence=1.5,
            reason="bad",
        )


# --- Fallback heuristic (offline, no LLM spend) ---


def test_fallback_coding():
    d = fallback_classify("Debug this python function, it throws an error")
    assert (d.task_type, d.capability) == ("coding", "coding")


def test_fallback_summarization():
    d = fallback_classify("Summarize this article in three sentences")
    assert d.task_type == "summarization"
    assert d.complexity == "low"


def test_fallback_image():
    d = fallback_classify("Draw a logo of a fox for my startup")
    assert (d.task_type, d.capability) == ("image", "image")
    assert d.quality_required == "high"


def test_fallback_math():
    d = fallback_classify("Solve 12 * (7 + 5) for me")
    assert d.task_type == "math"
    assert d.capability == "reasoning"


def test_fallback_general_qa():
    d = fallback_classify("What is the capital of France?")
    assert d.task_type == "general_qa"


def test_fallback_confidence_below_threshold():
    """Fallback must stay under the Phase 2 threshold so Phase 4 escalates."""
    for prompt in [
        "Debug this function",
        "Summarize this",
        "Draw a logo",
        "Solve 2+2",
        "Hello there",
    ]:
        assert fallback_classify(prompt).confidence < settings.confidence_threshold


# --- classify_prompt paths ---


def test_classify_no_keys_uses_fallback():
    decision, model_used, latency_ms, tokens = classify_prompt(
        "Debug this function", app_settings=_offline_settings()
    )
    assert model_used == FALLBACK_MODEL
    assert decision.task_type == "coding"
    assert tokens is None
    assert latency_ms >= 0


def test_classify_live_path_mocked(monkeypatch):
    payload = {
        "task_type": "math",
        "complexity": "high",
        "capability": "reasoning",
        "quality_required": "high",
        "confidence": 0.92,
        "reason": "Advanced math content.",
    }

    def fake_call(prompt, cfg):
        assert cfg.mistral_api_key == "test-mistral-key"  # provider key, not LangSmith
        return payload, 123

    monkeypatch.setattr("app.router.agent._call_mistral", fake_call)
    cfg = _offline_settings(
        mistral_api_key="test-mistral-key", classifier_model="mistral-large-latest"
    )
    decision, model_used, _, tokens = classify_prompt("Some integral", app_settings=cfg)
    assert model_used == "mistral-large-latest"
    assert decision.confidence == 0.92
    assert tokens == 123


def test_classify_bad_live_payload_falls_back(monkeypatch):
    monkeypatch.setattr(
        "app.router.agent._call_mistral", lambda prompt, cfg: ({"nope": 1}, None)
    )
    cfg = _offline_settings(mistral_api_key="k")
    decision, model_used, _, _ = classify_prompt("Summarize this", app_settings=cfg)
    assert model_used == FALLBACK_MODEL
    assert decision.task_type == "summarization"


# --- Tracing: LangSmith key only ---


def test_tracing_noop_without_key(monkeypatch):
    monkeypatch.delenv("LANGCHAIN_API_KEY", raising=False)
    assert setup_tracing(_offline_settings()) is False
    assert "LANGCHAIN_API_KEY" not in os.environ


def test_tracing_uses_langsmith_key_only(monkeypatch):
    cfg = _offline_settings(
        langchain_api_key="ls-key", mistral_api_key="mistral-key"
    )
    assert setup_tracing(cfg) is True
    assert os.environ["LANGCHAIN_API_KEY"] == "ls-key"  # never the inference key
    assert os.environ["LANGCHAIN_PROJECT"] == cfg.langchain_project


# --- API ---


def test_classify_endpoint_shape(monkeypatch):
    decision = RouterDecision(
        task_type="coding",
        complexity="low",
        capability="coding",
        quality_required="standard",
        confidence=0.8,
        reason="Mocked.",
    )
    # NOTE: importlib (not attribute path) because app/router/__init__.py
    # re-exports `router` (the APIRouter), shadowing the submodule attribute.
    router_module = importlib.import_module("app.router.router")
    monkeypatch.setattr(
        router_module,
        "classify_prompt",
        lambda prompt: (decision, "mistral-large-latest", 12.5, 100),
    )
    resp = client.post("/router/classify", json={"prompt": "Debug this function"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["decision"]["task_type"] == "coding"
    assert body["decision"]["confidence"] == 0.8
    assert body["model_used"] == "mistral-large-latest"
    assert body["latency_ms"] == 12.5
    assert body["tokens_used"] == 100


def test_classify_endpoint_empty_422():
    assert client.post("/router/classify", json={"prompt": "   "}).status_code == 422


def test_classify_endpoint_oversize_422():
    big = "x" * (settings.max_prompt_chars + 1)
    assert client.post("/router/classify", json={"prompt": big}).status_code == 422
