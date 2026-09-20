"""core/errors.py — иерархия исключений + классификация."""
from __future__ import annotations


class AppError(Exception):
    """Базовая ошибка проекта."""


class ConfigError(AppError):
    """Ошибка конфига."""


class LLMError(AppError):
    """Базовая ошибка LLM."""


class LLMFatalError(LLMError):
    """Не повторять: 400, 401, 403."""


class LLMRetryableError(LLMError):
    """Повторить: 429, 5xx, timeout."""


def classify_exception(exc: BaseException) -> LLMError:
    """Преобразовать любое исключение в LLMError."""
    msg = str(exc)
    status = getattr(exc, "status_code", None) or getattr(exc, "http_status", None)

    if status in (400, 401, 403):
        return LLMFatalError(f"HTTP {status}: {msg}")

    if status is not None and status >= 500:
        return LLMRetryableError(f"HTTP {status}: {msg}")

    if status == 429:
        return LLMRetryableError(f"HTTP 429: {msg}")

    low = msg.lower()
    if any(k in low for k in ("timeout", "connection", "temporarily", "retry")):
        return LLMRetryableError(msg)

    return LLMRetryableError(msg)
