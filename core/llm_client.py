"""
core/llm_client.py — универсальный клиент LLM с ретраями.

Оборачивает ЛЮБУЮ функцию, которая делает API-запрос,
и добавляет:
    - экспоненциальный backoff при 429/5xx/timeout
    - жёсткий лимит попыток
    - классификацию ошибок (retryable vs fatal)
    - колбэк для логирования

Не знает про конкретный SDK. Работает с openai, gigachat, requests — с чем угодно.

Пример:
    import openai
    client = openai.OpenAI(api_key=...)

    def _call(messages, **kw):
        return client.chat.completions.create(
            model="deepseek-chat", messages=messages, **kw
        )

    llm = LLMClient(_call, max_retries=3)
    response = llm.call(messages=[{"role":"user","content":"Привет"}])
"""
from __future__ import annotations

import time
from typing import Any, Callable, Optional

from core.errors import (
    LLMError,
    LLMFatalError,
    LLMRetryableError,
)


class LLMClient:
    """
    Обёртка над функцией-вызовом LLM.

    Аргументы:
        call_fn       — функция, выполняющая запрос. Принимает те же
                        аргументы, что передаются в .call().
        max_retries   — максимум ПОВТОРНЫХ попыток (не считая первой).
                        Итого запросов: max_retries + 1.
        base_delay    — базовая задержка в секундах. Реальная задержка
                        на попытке N: base_delay * (2 ** N), ограничена max_delay.
        max_delay     — потолок задержки.
        sleep_fn      — функция сна. По умолчанию time.sleep. Для тестов
                        можно подсунуть no-op, чтобы не ждать.
        on_retry      — колбэк (attempt, delay, error). Для логирования.
    """

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
        if max_retries < 0:
            raise ValueError("max_retries должен быть >= 0")
        if base_delay <= 0:
            raise ValueError("base_delay должен быть > 0")
        if max_delay < base_delay:
            raise ValueError("max_delay должен быть >= base_delay")

        self.call_fn = call_fn
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.sleep_fn = sleep_fn
        self.on_retry = on_retry
        self.attempts_log: list[dict] = []

    def call(self, *args, **kwargs) -> Any:
        """
        Вызвать call_fn с ретраями.

        Бросает:
            LLMFatalError     — если ошибка не подлежит повтору (401, 403, 400)
            LLMRetryableError — если попытки исчерпаны
        """
        last_error: Optional[LLMError] = None

        for attempt in range(self.max_retries + 1):
            try:
                result = self.call_fn(*args, **kwargs)
                self.attempts_log.append({"attempt": attempt, "result": "ok"})
                return result

            except Exception as raw:
                classified = _classify(raw)
                self.attempts_log.append(
                    {
                        "attempt": attempt,
                        "result": "fail",
                        "error_type": type(classified).__name__,
                        "error": str(classified)[:200],
                    }
                )

                if isinstance(classified, LLMFatalError):
                    raise classified from raw

                last_error = classified

                if attempt >= self.max_retries:
                    raise classified from raw

                delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                if self.on_retry is not None:
                    try:
                        self.on_retry(attempt, delay, classified)
                    except Exception:
                        pass
                self.sleep_fn(delay)

        # Сюда не должны попасть, но на всякий
        if last_error is not None:
            raise last_error
        raise LLMError("LLMClient.call: неизвестное состояние")


def _classify(exc: BaseException) -> LLMError:
    """Локальный импорт, чтобы избежать цикла и облегчить тесты."""
    from core.errors import classify_exception

    return classify_exception(exc)