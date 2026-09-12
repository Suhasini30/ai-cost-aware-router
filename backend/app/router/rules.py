"""Data-driven router rule table (no hardcoded routing logic elsewhere).

Matching DATA lives here as plain dicts/lists; every tunable threshold,
keyword list, and tier map comes from Settings (env-configurable).
agent.py / policy.py / evaluator.py interpret this table — they contain
no routing literals of their own.
"""

import re

from app.core.config import Settings, settings
from app.models.registry import Tier

# --- Rule table ------------------------------------------------------------
# "match" kinds: "startswith" (any prefix), "greeting" (exact word or
# word-followed-by-space/comma), "short_qa" (prefix + length + exclusions).
DEFAULT_RULES: list[dict] = [
    {
        "id": "classification",
        "match": "startswith",
        "patterns": ["classify ", "categorize ", "label ",
                     "sentiment of ", "is this spam"],
        "task_type": "classification",
        "capability": "text",
        "complexity": "low",
        "quality_required": "standard",
        "reason": "Fast Rule: obvious text classification request.",
    },
    {
        "id": "extraction",
        "match": "startswith",
        "patterns": ["extract ", "get keywords from", "parse json from",
                     "extract email"],
        "task_type": "extraction",
        "capability": "text",
        "complexity": "low",
        "quality_required": "standard",
        "reason": "Fast Rule: obvious data extraction request.",
    },
    {
        "id": "summarization",
        "match": "startswith",
        "patterns": ["summarize ", "tldr:", "tl;dr", "shorten this text:"],
        "task_type": "summarization",
        "capability": "text",
        "complexity": "low",
        "quality_required": "standard",
        "reason": "Fast Rule: obvious summarization request.",
    },
    {
        "id": "translate",
        "match": "startswith",
        "patterns": ["translate ", "translate this ", "translation of "],
        "task_type": "general_qa",
        "capability": "text",
        "complexity": "low",
        "quality_required": "standard",
        "reason": "Fast Rule: obvious translation request.",
    },
    {
        "id": "greeting",
        "match": "greeting",
        "patterns": ["hello", "hi", "hey", "good morning",
                     "good afternoon", "good evening", "greetings", "howdy"],
        "task_type": "general_qa",
        "capability": "text",
        "complexity": "low",
        "quality_required": "standard",
        "reason": "Fast Rule: simple greeting.",
    },
    {
        "id": "short_summarize",
        "match": "startswith",
        "patterns": ["summarize:", "summarise ", "summarise:"],
        "task_type": "summarization",
        "capability": "text",
        "complexity": "low",
        "quality_required": "standard",
        "reason": "Fast Rule: obvious summarization request.",
    },
    {
        "id": "simple_qa",
        "match": "short_qa",
        "patterns": ["what is ", "who is ", "where is ", "when was "],
        "exclude": ["why", "how to build", "architecture", "complex",
                    "explain in detail"],
        "task_type": "general_qa",
        "capability": "text",
        "complexity": "low",
        "quality_required": "standard",
        "reason": "Fast Rule: simple factual Q&A.",
    },
]


def _match_startswith(text: str, patterns: list[str]) -> bool:
    return any(text.startswith(p) for p in patterns)


def _match_greeting(text: str, patterns: list[str]) -> bool:
    return any(text == p or text.startswith(p + " ") or
               text.startswith(p + ",") for p in patterns)


def _match_short_qa(text: str, patterns: list[str], exclude: list[str],
                    max_chars: int) -> bool:
    return (any(text.startswith(p) for p in patterns)
            and len(text) < max_chars
            and not any(kw in text for kw in exclude))


def match_rules(text: str, rules: list[dict] | None = None, *,
                max_simple_qa_chars: int = 80) -> dict | None:
    """First matching rule dict, or None (fall through to LLM)."""
    for rule in DEFAULT_RULES if rules is None else rules:
        kind = rule.get("match", "startswith")
        if kind == "startswith" and _match_startswith(
                text, rule["patterns"]):
            return rule
        if kind == "greeting" and _match_greeting(text, rule["patterns"]):
            return rule
        if kind == "short_qa" and _match_short_qa(
                text, rule["patterns"], rule.get("exclude", []),
                max_simple_qa_chars):
            return rule
    return None


# --- Fallback pattern data (exact current behaviour, as data) -------------

DEFAULT_FALLBACK_PATTERNS: dict[str, str] = {
    "image": ("image|images|draw|drawing|paint|picture|photo|logo|"
              "illustration|diagram"),
    "code": ("code|coding|debug|function|class|bug|script|program|api|"
             "sql|refactor|compile|deploy"),
    "math": ("calculat|solve|equation|math|integral|derivative|algebra|"
             "statistic|percent|theorem|proof"),
    "summary": r"summar\w*|tldr|tl;dr|shorten\w*|condens\w*|recap",
    "classify": (r"classif\w*|categor\w*|sentiment|spam|ham|label\b|"
                 r"labels|tag\b|tags"),
    "extract": (r"extract\w*|entit\w*|keywords?|key phrases?|parse|"
                r"line items?|fields?"),
}


def compile_category_patterns(
        table: dict[str, str] | None = None) -> dict[str, "re.Pattern"]:
    """Compile one word-boundary regex per fallback category."""
    source = DEFAULT_FALLBACK_PATTERNS if table is None else table
    return {name: re.compile(rf"\b({inner})\b")
            for name, inner in source.items()}


def compile_complexity_pattern(keywords: list[str]) -> "re.Pattern":
    """Compile the (config-driven) high-complexity keyword pattern."""
    inner = "|".join(re.escape(k) for k in keywords)
    return re.compile(rf"\b({inner})\b") if inner else re.compile(r"(?!)")


def looks_like_math_expression(text: str) -> bool:
    """Digits combined with arithmetic operators (structural check)."""
    return bool(re.search(r"\d", text) and re.search(r"[+\-*/=^]", text))


# --- Tier-map + judge helpers (parse config strings) -----------------------

def tiers_from_map_value(raw: str) -> set[Tier]:
    """'fast' -> {FAST}, 'strong' -> {STRONG}, 'any' -> both.

    Raises ValueError on unknown tier names (fail fast on bad env).
    """
    raw = (raw or "").strip().lower()
    if raw == "any":
        return {Tier.FAST, Tier.STRONG}
    if raw in ("fast", "strong"):
        return {Tier(raw)}
    raise ValueError(f"Unknown tier in router map: {raw!r}")


def judge_task_types(cfg: Settings | None = None) -> set[str]:
    """Task types that trigger the quality judge (lowercased)."""
    source = cfg or settings
    return {t.strip().lower()
            for t in source.router_judge_task_types.split(",") if t.strip()}
