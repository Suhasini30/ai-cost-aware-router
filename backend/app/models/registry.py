"""Static model registry — data + lookups only.

Routing intelligence (confidence checks, cost/quality trade-offs,
fallback chains) lives in Phase 4, NOT here. Helpers below are pure
lookups over the static REGISTRY.
"""

from enum import Enum

from pydantic import BaseModel, Field


class Provider(str, Enum):
    MISTRAL = "mistral"
    GEMINI = "gemini"


class Tier(str, Enum):
    FAST = "fast"
    STRONG = "strong"


class ModelSpec(BaseModel):
    """Static descriptor for one LLM entry."""

    id: str = Field(description="Registry key, e.g. 'mistral-fast'")
    provider: Provider
    api_id: str = Field(description="Provider API model id, e.g. 'mistral-small-latest'")
    display_name: str
    tier: Tier

    # Pricing in USD per 1K tokens (separate directions for cost-aware routing).
    input_cost_per_1k: float = Field(ge=0.0)
    output_cost_per_1k: float = Field(ge=0.0)

    # Context / generation limits (tokens).
    context_window: int = Field(gt=0)
    max_output_tokens: int = Field(gt=0)

    # Static capability tags, e.g. ["chat", "reasoning", "code", "vision"].
    capabilities: list[str] = Field(default_factory=list)

    enabled: bool = True


REGISTRY: dict[str, ModelSpec] = {
    "mistral-fast": ModelSpec(
        id="mistral-fast",
        provider=Provider.MISTRAL,
        api_id="mistral-small-latest",
        display_name="Mistral Fast",
        tier=Tier.FAST,
        input_cost_per_1k=0.0001,  # ~$0.10 / 1M
        output_cost_per_1k=0.0003,  # ~$0.30 / 1M
        context_window=128000,
        max_output_tokens=8192,
        capabilities=["chat", "summarization", "classification", "code-assist"],
    ),
    "mistral-strong": ModelSpec(
        id="mistral-strong",
        provider=Provider.MISTRAL,
        api_id="mistral-large-latest",
        display_name="Mistral Strong",
        tier=Tier.STRONG,
        input_cost_per_1k=0.002,  # ~$2.00 / 1M
        output_cost_per_1k=0.006,  # ~$6.00 / 1M
        context_window=128000,
        max_output_tokens=8192,
        capabilities=["chat", "reasoning", "code", "multilingual", "long-context"],
    ),
    "gemini-fast": ModelSpec(
        id="gemini-fast",
        provider=Provider.GEMINI,
        api_id="gemini-1.5-flash",
        display_name="Gemini Fast",
        tier=Tier.FAST,
        input_cost_per_1k=0.000075,  # ~$0.075 / 1M
        output_cost_per_1k=0.0003,  # ~$0.30 / 1M
        context_window=1048576,
        max_output_tokens=8192,
        capabilities=["chat", "summarization", "classification", "long-context"],
    ),
    "gemini-strong": ModelSpec(
        id="gemini-strong",
        provider=Provider.GEMINI,
        api_id="gemini-1.5-pro",
        display_name="Gemini Strong",
        tier=Tier.STRONG,
        input_cost_per_1k=0.00125,  # ~$1.25 / 1M
        output_cost_per_1k=0.005,  # ~$5.00 / 1M
        context_window=1048576,
        max_output_tokens=8192,
        capabilities=["chat", "reasoning", "code", "vision", "long-context"],
    ),
}


def list_providers() -> list[str]:
    """Return distinct provider values present in the registry."""
    return sorted({spec.provider.value for spec in REGISTRY.values()})


def list_models(provider: str | None = None) -> list[ModelSpec]:
    """List models, optionally filtered by provider.

    Raises:
        ValueError: if `provider` matches no registered provider.
    """
    if provider is None:
        return list(REGISTRY.values())
    key = provider.lower()
    if key not in list_providers():
        raise ValueError(f"Unknown provider: {provider!r}")
    return [spec for spec in REGISTRY.values() if spec.provider.value == key]


def get_model(model_id: str) -> ModelSpec:
    """Return one model by registry id.

    Raises:
        KeyError: if `model_id` is not registered.
    """
    try:
        return REGISTRY[model_id]
    except KeyError:
        raise KeyError(f"Unknown model: {model_id!r}") from None


def _scope(provider: str | None) -> list[ModelSpec]:
    """Shared provider-scoped view (validates provider via list_models)."""
    return list_models(provider)


def get_cheapest_model(provider: str | None = None) -> ModelSpec:
    """Cheapest model by combined input+output price within scope.

    Pure data lookup — no confidence/threshold logic (Phase 4 decides
    *when* to prefer cheap vs strong).
    """
    candidates = _scope(provider)
    return min(
        candidates, key=lambda m: (m.input_cost_per_1k + m.output_cost_per_1k, m.id)
    )


def get_strong_model(provider: str | None = None) -> ModelSpec:
    """Strong-tier model within scope (cheapest strong on ties).

    Pure data lookup — no routing policy here.

    Raises:
        ValueError: if no strong-tier model exists in scope.
    """
    candidates = [m for m in _scope(provider) if m.tier == Tier.STRONG]
    if not candidates:
        scope = provider or "global"
        raise ValueError(f"No strong-tier model in scope: {scope!r}")
    return min(
        candidates, key=lambda m: (m.input_cost_per_1k + m.output_cost_per_1k, m.id)
    )
