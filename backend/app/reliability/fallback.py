"""Alternative-provider selection (Phase 7).

When the routed provider fails operationally, fall back to a different
provider's model that satisfies the SAME capability (and tier) — never
just any available model. Reads the registry; pure lookup, no I/O.
"""

from app.models.registry import CAPABILITY_TAGS, ModelSpec, Tier, list_models


def _cost_key(m: ModelSpec) -> tuple[float, str]:
    return (m.input_cost_per_1k + m.output_cost_per_1k, m.id)


def alternatives(
    *,
    capability: str | None,
    tier: Tier | str | None = None,
    exclude_provider: str | None = None,
    exclude_model: str | None = None,
) -> list[ModelSpec]:
    """Capable replacement models, cheapest summed price first.

    Same-tier + capability-tag match + different provider + enabled.
    Callers without capability context get no pool (same-provider
    retries only) rather than a capability-blind guess.
    """
    if capability is None:
        return []
    required = CAPABILITY_TAGS.get(capability, set())
    want_tier = Tier(tier) if tier is not None else None
    exclude_provider_normalized = (exclude_provider or "").lower()
    pool = []
    for m in list_models():
        if not m.enabled:
            continue
        if exclude_model is not None and m.id == exclude_model:
            continue
        if exclude_provider_normalized and (
            m.provider.value == exclude_provider_normalized
        ):
            continue
        if want_tier is not None and m.tier != want_tier:
            continue
        if required and not (required & set(m.capabilities)):
            continue
        pool.append(m)
    return sorted(pool, key=_cost_key)
