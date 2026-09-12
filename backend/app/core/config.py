from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve backend/.env regardless of CWD (uvicorn, pytest, etc.)
_BACKEND_DIR = Path(__file__).resolve().parents[2]
_ENV_FILE = _BACKEND_DIR / ".env"


class Settings(BaseSettings):
    app_name: str = "Cost-Aware Multi-Model Router"
    app_version: str = "1.0.0"
    debug: bool = True
    environment: str = "development"

    mistral_api_key: str | None = None
    gemini_api_key: str | None = None
    xai_api_key: str | None = None
    groq_api_key: str | None = None
    deepseek_api_key: str | None = None

    langchain_tracing_v2: bool = True
    langchain_api_key: str | None = None
    langchain_project: str = "cost-aware-router"

    confidence_threshold: float = Field(default=0.75, ge=0.0, le=1.0)

    # ── Router Rule Engine ────────────────────────────────────────────────────
    # All values default to current behaviour — zero-change upgrade.

    # Prompt length (chars) at or above which a coding/math fallback decision
    # is treated as "complex" (overrides complexity="low" from LLM classifier).
    router_complexity_long_prompt_chars: int = Field(default=200, gt=0)

    # Max prompt length (chars) for the simple-factual-QA rule to fire.
    router_rule_max_simple_qa_chars: int = Field(default=80, gt=0)

    # Minimum answer length (chars) below which the judge gate always runs.
    router_judge_min_answer_chars: int = Field(default=20, gt=0)

    # Comma-separated task_types that always trigger the quality judge.
    router_judge_task_types: str = "coding,math,reasoning"

    # Comma-separated keywords that signal "high complexity" in the
    # fallback classifier (used when the LLM classifier is unavailable).
    router_high_complexity_keywords: str = (
        "complex,algorithm,architect,optimiz,distributed,"
        "concurren,production,critical"
    )

    # Complexity → tier mapping: comma-separated "complexity:tier" pairs.
    # "low:fast" means complexity=low → FAST tier; anything else → STRONG.
    router_complexity_tier_map: str = "low:fast"

    # quality_required → tier override: comma-separated "quality:tier" pairs.
    # "high:strong" means quality_required=high always escalates to STRONG.
    router_quality_tier_map: str = "high:strong"

    # Override the LLM classifier system prompt (leave empty for default).
    router_classifier_system_prompt: str = ""

    # Phase 3 classifier: FIXED strongest model (accuracy first).
    # NOTE: cost-aware selection is Phase 4 — do NOT pick this dynamically.
    # LANGCHAIN_API_KEY is the LangSmith tracing key only; it is never
    # used for inference and never interchanged with provider keys above.
    classifier_model: str = "mistral-large-latest"
    classifier_provider: str = "mistral"
    classifier_timeout_s: float = Field(default=20.0, gt=0.0)
    max_prompt_chars: int = Field(default=4000, gt=0)

    # Phase 5 execution service: generic inference calls (answer flow).
    # Separate from the classifier's budget on purpose.
    execution_timeout_s: float = Field(default=30.0, gt=0.0)
    execution_max_tokens: int = Field(default=1024, gt=0)

    # Phase 7 reliability: same-provider retries + capable-provider
    # failover inside the execution service. Transport errors only —
    # never answer content (quality stays Phase 6's job).
    reliability_max_retries: int = Field(default=2, ge=0)
    reliability_backoff_base_s: float = Field(default=0.5, ge=0.0)
    max_escalations: int = Field(default=1, ge=0)
    max_total_model_calls: int = Field(default=4, ge=1)

    # Phase 6 quality judge: FIXED strongest model (accuracy first),
    # like the classifier. quality_pass_threshold is ANSWER quality and
    # must never be confused with confidence_threshold (classification).
    judge_model: str = "mistral-large-latest"
    judge_provider: str = "mistral"
    quality_pass_threshold: float = Field(default=0.7, ge=0.0, le=1.0)

    # Phase 10 Clerk auth: public, non-secret endpoint config. The .env
    # already carries Clerk secret keys, but those alone are NOT enough —
    # the JWKS URL and issuer below must be configured by the operator.
    # Empty values fail closed (every token → 401), never open.
    clerk_jwks_url: str = ""
    clerk_issuer: str = ""
    clerk_jwks_cache_ttl_s: float = Field(default=600.0, gt=0.0)

    # Browser dashboard support: origins allowed by CORS (dev defaults
    # cover localhost/127.0.0.1 on the usual Next.js ports — the UI may
    # run on :3000 or :3001, and both spellings of localhost occur).
    frontend_origins: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ]

    # Observability: stdout log verbosity (LOG_LEVEL env overrides).
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    # Backend token sessions: HS256 self-minted access + refresh tokens.
    # jwt_secret_key is REQUIRED (fail closed when empty) and must be
    # generated by the operator, e.g. secrets.token_urlsafe(48).
    # Never commit it; .env only.
    jwt_secret_key: str = ""
    jwt_access_minutes: int = Field(default=15, gt=0)
    jwt_refresh_days: int = Field(default=7, gt=0)
    refresh_cookie_name: str = "rt"

    # Phase 11 MongoDB & Persistence Settings (names match backend/.env).
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_database: str = "cost_aware_router"

    # Privacy Controls for Query Persistence
    privacy_store_prompts: bool = True
    privacy_store_answers: bool = True
    privacy_store_execution_trace: bool = True
    privacy_anonymize_user: bool = False

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @model_validator(mode="after")
    def validate_classifier_model(self) -> "Settings":
        provider = self.classifier_provider.lower()
        model = self.classifier_model.lower()
        if provider == "gemini" and "gemini" not in model:
            raise ValueError(f"Model {self.classifier_model} is not compatible with provider gemini")
        if provider == "mistral" and "mistral" not in model and "mixtral" not in model:
            raise ValueError(f"Model {self.classifier_model} is not compatible with provider mistral")
        return self

    # ── Derived helpers (computed once from env strings) ──────────────────────

    def judge_task_type_set(self) -> set[str]:
        """Parsed set of task_types that trigger the quality judge."""
        return {t.strip() for t in self.router_judge_task_types.split(",") if t.strip()}

    def high_complexity_keyword_list(self) -> list[str]:
        """Parsed list of keywords signalling high complexity in fallback."""
        return [k.strip() for k in self.router_high_complexity_keywords.split(",") if k.strip()]

    def complexity_tier_map(self) -> dict[str, str]:
        """Parsed complexity→tier mapping dict, e.g. {'low': 'fast'}."""
        result: dict[str, str] = {}
        for pair in self.router_complexity_tier_map.split(","):
            pair = pair.strip()
            if ":" in pair:
                k, v = pair.split(":", 1)
                result[k.strip()] = v.strip()
        return result

    def quality_tier_map(self) -> dict[str, str]:
        """Parsed quality_required→tier override dict, e.g. {'high': 'strong'}."""
        result: dict[str, str] = {}
        for pair in self.router_quality_tier_map.split(","):
            pair = pair.strip()
            if ":" in pair:
                k, v = pair.split(":", 1)
                result[k.strip()] = v.strip()
        return result


settings = Settings()