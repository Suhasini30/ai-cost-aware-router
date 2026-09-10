"""Provider execution layer (Phase 5).

Router code must not contain provider-specific calls: every LLM
invocation goes through Execution Service → Provider Factory →
one ProviderAdapter per vendor. All adapters share one interface.
"""

from abc import ABC, abstractmethod
from typing import Any, Callable

from pydantic import BaseModel

try:  # langsmith is optional at runtime; tests/dev work without it
    from langsmith import traceable
except ImportError:  # pragma: no cover - exercised when langsmith missing

    def traceable(*args: Any, **kwargs: Any) -> Callable:
        if len(args) == 1 and callable(args[0]) and not kwargs:
            return args[0]

        def wrap(fn: Callable) -> Callable:
            return fn

        return wrap


class ExecutionResult(BaseModel):
    """Uniform outcome of one provider call."""

    text: str
    provider: str
    model_api_id: str
    latency_ms: float
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None


class ProviderAdapter(ABC):
    """Common interface every vendor adapter implements."""

    provider: str

    def __init__(self, api_key: str, timeout_s: float = 30.0, max_tokens: int = 1024):
        if not api_key:
            raise ValueError(f"Missing API key for provider {self.provider!r}")
        self.api_key = api_key
        self.timeout_s = timeout_s
        self.max_tokens = max_tokens

    @abstractmethod
    def execute(
        self,
        *,
        model_api_id: str,
        prompt: str,
        system_prompt: str | None = None,
        json_mode: bool = False,
    ) -> ExecutionResult:
        """Run one chat-style call; transport errors propagate."""
        raise NotImplementedError
