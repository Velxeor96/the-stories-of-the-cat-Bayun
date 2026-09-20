"""core/llm_client.py — обёртка retry/backoff над call_fn."""
from __future__ import annotations

import time
from typing import Any, Callable, Optional

from core.errors import (
    LLMError,
    LLMFatalError,
    LLMRetryableError,
    classify_exception,
)


class LLMClient:
    def __init__(
        self,
        call_fn: Callable[..., Any],
        *,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
        sleep_fn: Callable[[float], None] = time.sleep,
        on_retry: Optional[Callable[[int, float, LLMError], None]] = None,
    ):
        self.call_fn = call_fn
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.sleep_fn = sleep_fn
        self.on_retry = on_retry
        self.attempts_log: list[dict] = []

    def call(self, *args, **kwargs) -> Any:
        last_error: Optional[LLMError] = None

        for attempt in range(self.max_retries + 1):
            try:
                result = self.call_fn(*args, **kwargs)
                self.attempts_log.append({"attempt": attempt, "result": "ok"})
                return result
            except Exception as raw:
                classified = classify_exception(raw)
                self.attempts_log.append({
                    "attempt": attempt, "result": "fail",
                    "error_type": type(classified).__name__,
                    "error": str(classified)[:200],
                })
                if isinstance(classified, LLMFatalError):
                    raise classified from raw
                last_error = classified
                if attempt >= self.max_retries:
                    raise classified from raw
                delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                if self.on_retry:
                    try:
                        self.on_retry(attempt, delay, classified)
                    except Exception:
                        pass
                self.sleep_fn(delay)

        if last_error is not None:
            raise last_error
        raise LLMError("LLMClient: неизвестное состояние")
