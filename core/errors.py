"""
core/errors.py — иерархия ошибок LLM + классификатор исключений.

Задача:
    Отделить ошибки, которые ИМЕЕТ СМЫСЛ повторить (429, 5xx, timeout),
    от тех, которые повторять бесполезно (401, 403, 400).

Как работает:
    Сторонние SDK (openai, gigachat) кидают СВОИ исключения.
    Мы их ловим, классифицируем через classify_exception(),
    и возвращаем либо LLMRetryableError, либо LLMFatalError.
    LLMClient (core/llm_client.py) уже знает, что делать.
"""
from __future__ import annotations


class LLMError(Exception):
    """Базовый класс для всех ошибок LLM."""


class LLMFatalError(LLMError):
    """
    Ошибка, которую бессмысленно повторять.

    Примеры: неверный API-ключ (401), нет доступа (403),
    невалидный запрос (400), модель не найдена (404).
    """


class LLMRetryableError(LLMError):
    """
    Временная ошибка. Имеет смысл повторить запрос.

    Примеры: 429 (rate limit), 500/502/503/504,
    таймауты, сетевые обрывы.
    """


class LLMTimeoutError(LLMRetryableError):
    """Отдельный подкласс — для ясности в логах."""


# ============================================================
# Классификатор
# ============================================================

# HTTP-статусы, которые повторяем
_RETRYABLE_STATUS = {408, 409, 425, 429, 500, 502, 503, 504}

# HTTP-статусы, которые НЕ повторяем
_FATAL_STATUS = {400, 401, 403, 404, 405, 422}


def classify_exception(exc: BaseException) -> LLMError:
    """
    Превратить произвольное исключение в один из наших классов.

    Логика:
    1. Если уже наше — вернуть как есть.
    2. Если есть .status_code (openai, httpx) — по нему.
    3. Если есть .response.status_code — по нему.
    4. Если в тексте есть "timeout" / "timed out" — retryable.
    5. Если в тексте есть "rate" / "429" / "too many" — retryable.
    6. Всё остальное — retryable (безопаснее повторить, чем уронить).
    """
    if isinstance(exc, LLMError):
        return exc

    status = _extract_status(exc)
    if status is not None:
        if status in _RETRYABLE_STATUS:
            return LLMRetryableError(f"HTTP {status}: {exc}")
        if status in _FATAL_STATUS:
            return LLMFatalError(f"HTTP {status}: {exc}")

    msg = str(exc).lower()

    if "timeout" in msg or "timed out" in msg:
        return LLMTimeoutError(str(exc))
    if "rate" in msg and "limit" in msg:
        return LLMRetryableError(str(exc))
    if "429" in msg or "too many requests" in msg:
        return LLMRetryableError(str(exc))
    if "connection" in msg and ("reset" in msg or "refused" in msg or "aborted" in msg):
        return LLMRetryableError(str(exc))

    # Неизвестное — считаем retryable
    return LLMRetryableError(str(exc))


def _extract_status(exc: BaseException) -> int | None:
    """Достать HTTP-статус из разных SDK."""
    for attr in ("status_code", "http_status", "code"):
        val = getattr(exc, attr, None)
        if isinstance(val, int):
            return val

    resp = getattr(exc, "response", None)
    if resp is not None:
        val = getattr(resp, "status_code", None)
        if isinstance(val, int):
            return val

    return None