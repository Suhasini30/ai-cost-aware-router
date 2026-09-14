import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import Settings
from app.main import app
from app.models.registry import (
    get_cheapest_model,
    get_model,
    get_strong_model,
    list_models,
)

client = TestClient(app)


# --- Config ---


def test_confidence_threshold_default():
    assert Settings().confidence_threshold == 0.75


def test_confidence_threshold_bounds_rejected():
    with pytest.raises(ValidationError):
        Settings(confidence_threshold=1.5)


# --- Registry integrity ---


def test_registry_has_four_models():
    models = list_models()
    assert len(models) == 4
    assert {m.id for m in models} == {
        "mistral-fast",
        "mistral-strong",
        "gemini-fast",
        "gemini-strong",
    }


def test_registry_api_ids():
    assert get_model("mistral-fast").api_id == "mistral-small-latest"
    assert get_model("mistral-strong").api_id == "mistral-large-latest"
    assert get_model("gemini-fast").api_id == "gemini-1.5-flash"
    assert get_model("gemini-strong").api_id == "gemini-1.5-pro"


def test_model_spec_full_fields():
    for m in list_models():
        assert m.input_cost_per_1k >= 0
        assert m.output_cost_per_1k >= 0
        assert m.context_window > 0
        assert m.max_output_tokens > 0
        assert isinstance(m.capabilities, list) and len(m.capabilities) > 0


def test_get_model_unknown_raises():
    with pytest.raises(KeyError):
        get_model("nope")


# --- Selection helpers (pure lookups, no routing policy) ---


def test_cheapest_per_provider():
    assert get_cheapest_model("mistral").id == "mistral-fast"
    assert get_cheapest_model("gemini").id == "gemini-fast"


def test_strong_per_provider():
    assert get_strong_model("mistral").id == "mistral-strong"
    assert get_strong_model("gemini").id == "gemini-strong"


def test_cheapest_global_is_min_input_price():
    cheapest = get_cheapest_model()
    assert cheapest.input_cost_per_1k == min(m.input_cost_per_1k for m in list_models())


def test_strong_global_is_strong_tier():
    assert get_strong_model().tier.value == "strong"


def test_unknown_provider_raises():
    with pytest.raises(ValueError):
        list_models("unknown-provider")


# --- API ---


def test_get_models_endpoint():
    resp = client.get("/models")
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == 4
    for item in body["models"]:
        for field in (
            "id",
            "provider",
            "api_id",
            "tier",
            "input_cost_per_1k",
            "output_cost_per_1k",
            "context_window",
            "max_output_tokens",
            "capabilities",
        ):
            assert field in item


def test_get_models_provider_filter():
    resp = client.get("/models", params={"provider": "mistral"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == 2
    assert all(m["provider"] == "mistral" for m in body["models"])


def test_get_models_bad_provider_400():
    resp = client.get("/models", params={"provider": "nope"})
    assert resp.status_code == 400


def test_get_model_by_id_and_404():
    assert client.get("/models/mistral-fast").status_code == 200
    assert client.get("/models/mistral-fast").json()["api_id"] == "mistral-small-latest"
    assert client.get("/models/nope").status_code == 404
