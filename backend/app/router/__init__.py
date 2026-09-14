"""Router package exports.

NOTE: the APIRouter lives in app.router.router and is NOT re-exported
here on purpose — importing it at package init creates a cycle with
app.eval.schemas (which needs app.router.schemas). Import it explicitly:
`from app.router.router import router`.
"""
from app.router.agent import FALLBACK_MODEL, classify_prompt, fallback_classify
from app.router.policy import route_decision, strongest_capable
from app.router.schemas import (
    ClassifyRequest,
    ClassifyResponse,
    RouteRequest,
    RouteResponse,
    RouteStage,
    RouterDecision,
)

__all__ = [
    "FALLBACK_MODEL",
    "classify_prompt",
    "fallback_classify",
    "route_decision",
    "strongest_capable",
    "ClassifyRequest",
    "ClassifyResponse",
    "RouteRequest",
    "RouteResponse",
    "RouteStage",
    "RouterDecision",
]
