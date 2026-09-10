import importlib

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.registry import ModelSpec, Provider, Tier, get_cheapest_model
from app.models import registry as registry_module
from app.router.policy import route_decision
from app.router.schemas import RouterDecision

client = TestClient(app)

router_module = importlib.import_module("app.router.router")


def _decision(**overrides):
    base = dict(
        task_type="general_qa",
        complexity="low",
        capability="text",
        quality_required="standard",
        confidence=0.9,
        reason="test",
    )
    base.update(overrides)
    return RouterDecision(**base)


# --- Worked example (real registry prices) ---


def test_worked_example_selects_gemini_fast():
    selected, trace, fallback = route_decision(_decision())
    assert selected.id == "gemini-fast"
    assert fallback is False
    assert [s.stage for s in trace] == [
        "capability",
        "confidence",
        "complexity",
        "quality",
    ]


# --- Confidence gate ---


def test_low_confidence_escalates_to_strong():
    selected, trace, fallback = route_decision(_decision(confidence=0.6))
    assert selected.tier == Tier.STRONG
    assert selected.id == "gemini-strong"  # cheapest strong, summed price
    assert fallback is False
    assert "escalate" in trace[1].rule


# --- Tier gates ---


def test_coding_high_selects_cheapest_strong_with_code():
    selected, _, fallback = route_decision(
        _decision(
            task_type="coding",
            complexity="high",
            capability="coding",
            confidence=0.9,
        )
    )
    assert selected.id == "gemini-strong"
    assert fallback is False


def test_image_selects_only_vision_model():
    selected, trace, _ = route_decision(
        _decision(
            task_type="image",
            complexity="high",
            capability="image",
            quality_required="high",
            confidence=0.9,
        )
    )
    assert selected.id == "gemini-strong"
    assert trace[0].kept == ["gemini-strong"]


def test_low_complexity_high_quality_forces_strong():
    selected, _, fallback = route_decision(
        _decision(quality_required="high", confidence=0.9)
    )
    assert selected.tier == Tier.STRONG
    assert fallback is False


# --- Summed cost key (Correction #3) ---


def test_summed_cost_key_beats_input_only():
    """A cheap-input/expensive-output model must lose to a balanced one."""
    pricey_out = ModelSpec(
        id="syn-a",
        provider=Provider.MISTRAL,
        api_id="syn-a",
        display_name="Syn A",
        tier=Tier.FAST,
        input_cost_per_1k=0.0001,
        output_cost_per_1k=0.01,
        context_window=8000,
        max_output_tokens=1000,
        capabilities=["chat"],
    )
    balanced = ModelSpec(
        id="syn-b",
        provider=Provider.MISTRAL,
        api_id="syn-b",
        display_name="Syn B",
        tier=Tier.FAST,
        input_cost_per_1k=0.0002,
        output_cost_per_1k=0.00005,
        context_window=8000,
        max_output_tokens=1000,
        capabilities=["chat"],
    )
    registry_module.REGISTRY["syn-a"] = pricey_out
    registry_module.REGISTRY["syn-b"] = balanced
    try:
        # Summed key picks syn-b (0.00025); input-only key would pick
        # gemini-fast (0.000075) — proving the corrected key behaves
        # differently from the old one.
        assert get_cheapest_model().id == "syn-b"
        assert (
            min(
                registry_module.list_models(),
                key=lambda m: (m.input_cost_per_1k, m.id),
            ).id
            == "gemini-fast"
        )
        selected, _, _ = route_decision(_decision())
        assert selected.id == "syn-b"
    finally:
        del registry_module.REGISTRY["syn-a"]
        del registry_module.REGISTRY["syn-b"]


# --- Safe fallback ---


def test_empty_capability_match_falls_back_strong(monkeypatch):
    monkeypatch.setattr(
        "app.router.policy.list_models",
        lambda provider=None: [
            m
            for m in registry_module.list_models(provider)
            if m.id != "gemini-strong"
        ],
    )
    selected, _, fallback = route_decision(
        _decision(
            task_type="image",
            complexity="high",
            capability="image",
            quality_required="high",
            confidence=0.9,
        )
    )
    assert fallback is True
    assert selected.tier == Tier.STRONG


# --- Sourcery review: enabled-only fallback, honest no-raise contract ---


def test_fallback_never_returns_disabled_model(monkeypatch):
    """A disabled strong model must not be selected (finding: policy.py:61)."""
    spec = registry_module.REGISTRY["gemini-strong"]
    monkeypatch.setattr(spec, "enabled", False)
    selected, _, fallback = route_decision(
        _decision(
            task_type="image",
            complexity="high",
            capability="image",
            quality_required="high",
            confidence=0.9,
        )
    )
    assert fallback is True
    assert selected.enabled is True
    assert selected.id == "mistral-strong"  # cheapest *enabled* strong


def test_fallback_without_any_strong_model(monkeypatch):
    """No strong tier anywhere → cheapest enabled, no raise (policy.py:42)."""
    fast_only = [
        m
        for m in registry_module.list_models()
        if m.tier == Tier.FAST
    ]
    monkeypatch.setattr(
        "app.router.policy.list_models", lambda provider=None: fast_only
    )
    selected, _, fallback = route_decision(
        _decision(
            task_type="image",
            complexity="high",
            capability="image",
            quality_required="high",
            confidence=0.9,
        )
    )
    assert fallback is True
    assert selected.id == "gemini-fast"  # cheapest enabled overall


def test_empty_registry_raises_explicitly(monkeypatch):
    """Zero enabled models is misconfiguration: ValueError, not a route."""
    monkeypatch.setattr("app.router.policy.list_models", lambda provider=None: [])
    with pytest.raises(ValueError, match="No enabled models"):
        route_decision(_decision())


# --- Correction #2 guard: confidence is classification-only ---


def test_no_answer_quality_field_on_decision():
    assert "answer_quality" not in RouterDecision.model_fields
    assert "quality" not in RouterDecision.model_fields  # only quality_required


# --- API ---


def test_route_endpoint_shape(monkeypatch):
    decision = _decision(
        task_type="coding", complexity="high", capability="coding", confidence=0.8
    )
    monkeypatch.setattr(
        router_module,
        "classify_prompt",
        lambda prompt: (decision, "mistral-large-latest", 10.0, 50),
    )
    resp = client.post("/router/route", json={"prompt": "Debug this function"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["decision"]["task_type"] == "coding"
    assert body["selected_model"]["id"] == "gemini-strong"
    assert body["classifier_model_used"] == "mistral-large-latest"
    assert body["fallback"] is False
    assert [s["stage"] for s in body["trace"]] == [
        "capability",
        "confidence",
        "complexity",
        "quality",
    ]


def test_route_endpoint_empty_422():
    assert client.post("/router/route", json={"prompt": "  "}).status_code == 422
