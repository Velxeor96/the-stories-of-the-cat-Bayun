r"""
Тесты core.llm_client и core.errors.

Запуск (из корня проекта):
    python tests\test_llm_client.py
"""
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.errors import (  # noqa: E402
    LLMError,
    LLMFatalError,
    LLMRetryableError,
    LLMTimeoutError,
    classify_exception,
)
from core.llm_client import LLMClient  # noqa: E402


# ============================================================
# Вспомогательные
# ============================================================

def assert_eq(actual, expected, label: str) -> bool:
    if actual != expected:
        print(f"[FAIL] {label}: ожидалось {expected!r}, получено {actual!r}")
        return False
    print(f"[ ok ] {label}: {actual!r}")
    return True


def assert_true(cond, label: str) -> bool:
    if not cond:
        print(f"[FAIL] {label}")
        return False
    print(f"[ ok ] {label}")
    return True


class FakeHTTPError(Exception):
    """Имитация ошибки SDK с .status_code (как у openai)."""

    def __init__(self, status_code: int, message: str = "fake error"):
        super().__init__(message)
        self.status_code = status_code


def make_flaky_call(fail_times: int, exc: Exception, then_return: Any = "OK"):
    """
    Создать функцию, которая падает fail_times раз, потом возвращает then_return.
    """
    counter = {"n": 0}

    def _call(*args, **kwargs):
        if counter["n"] < fail_times:
            counter["n"] += 1
            raise exc
        return then_return

    _call.counter = counter  # для проверки
    return _call


def noop_sleep(_delay: float) -> None:
    """Не ждём в тестах."""
    pass


# ============================================================
# Тесты классификатора
# ============================================================

def test_classify() -> bool:
    ok = True

    ok &= assert_true(
        isinstance(classify_exception(LLMFatalError("x")), LLMFatalError),
        "классификация: уже наш FatalError",
    )
    ok &= assert_true(
        isinstance(classify_exception(FakeHTTPError(429)), LLMRetryableError),
        "429 → Retryable",
    )
    ok &= assert_true(
        isinstance(classify_exception(FakeHTTPError(500)), LLMRetryableError),
        "500 → Retryable",
    )
    ok &= assert_true(
        isinstance(classify_exception(FakeHTTPError(503)), LLMRetryableError),
        "503 → Retryable",
    )
    ok &= assert_true(
        isinstance(classify_exception(FakeHTTPError(401)), LLMFatalError),
        "401 → Fatal",
    )
    ok &= assert_true(
        isinstance(classify_exception(FakeHTTPError(403)), LLMFatalError),
        "403 → Fatal",
    )
    ok &= assert_true(
        isinstance(classify_exception(FakeHTTPError(400)), LLMFatalError),
        "400 → Fatal",
    )
    ok &= assert_true(
        isinstance(classify_exception(Exception("Request timed out")), LLMTimeoutError),
        "timeout в тексте → Timeout",
    )
    ok &= assert_true(
        isinstance(
            classify_exception(Exception("rate limit exceeded")),
            LLMRetryableError,
        ),
        "rate limit в тексте → Retryable",
    )
    ok &= assert_true(
        isinstance(classify_exception(Exception("что-то странное")), LLMRetryableError),
        "неизвестная → Retryable (безопасно)",
    )
    return ok


# ============================================================
# Тесты LLMClient
# ============================================================

def test_client_success_no_retry() -> bool:
    """Первый вызов успешен — никаких ретраев."""
    ok = True
    call = make_flaky_call(fail_times=0, exc=Exception("unused"), then_return="OK")
    llm = LLMClient(call, max_retries=3, sleep_fn=noop_sleep)

    result = llm.call()
    ok &= assert_eq(result, "OK", "успех с первого раза")
    ok &= assert_eq(call.counter["n"], 0, "не было вызовов-падений")
    ok &= assert_eq(len(llm.attempts_log), 1, "в логе 1 попытка")
    return ok


def test_client_retry_then_success() -> bool:
    """429 дважды, потом успех."""
    ok = True
    call = make_flaky_call(fail_times=2, exc=FakeHTTPError(429), then_return="PONG")
    llm = LLMClient(call, max_retries=3, sleep_fn=noop_sleep)

    result = llm.call()
    ok &= assert_eq(result, "PONG", "успех после 2 ретраев")
    ok &= assert_eq(call.counter["n"], 2, "функция упала 2 раза")
    ok &= assert_eq(len(llm.attempts_log), 3, "в логе 3 попытки")
    return ok


def test_client_retry_exhausted() -> bool:
    """Постоянно 429 — исчерпали попытки, бросаем."""
    ok = True
    call = make_flaky_call(fail_times=10, exc=FakeHTTPError(429), then_return="NEVER")
    llm = LLMClient(call, max_retries=2, sleep_fn=noop_sleep)

    try:
        llm.call()
        print("[FAIL] должен был бросить после исчерпания")
        ok = False
    except LLMRetryableError:
        print("[ ok ] после исчерпания → LLMRetryableError")

    ok &= assert_eq(call.counter["n"], 3, "функция вызвана 3 раза (1 + 2 retry)")
    return ok


def test_client_fatal_no_retry() -> bool:
    """401 — не повторяем, сразу бросаем."""
    ok = True
    call = make_flaky_call(fail_times=10, exc=FakeHTTPError(401), then_return="NEVER")
    llm = LLMClient(call, max_retries=3, sleep_fn=noop_sleep)

    try:
        llm.call()
        print("[FAIL] 401 должен был бросить сразу")
        ok = False
    except LLMFatalError:
        print("[ ok ] 401 → LLMFatalError сразу")

    ok &= assert_eq(call.counter["n"], 1, "функция вызвана 1 раз (без ретраев)")
    ok &= assert_eq(len(llm.attempts_log), 1, "в логе 1 попытка")
    return ok


def test_client_timeout_retryable() -> bool:
    """Timeout повторяем."""
    ok = True
    call = make_flaky_call(
        fail_times=1, exc=Exception("Request timed out"), then_return="OK"
    )
    llm = LLMClient(call, max_retries=2, sleep_fn=noop_sleep)

    result = llm.call()
    ok &= assert_eq(result, "OK", "после timeout → успех")
    return ok


def test_client_backoff_increases() -> bool:
    """Проверить, что задержка растёт экспоненциально."""
    ok = True

    delays: list[float] = []

    def record_sleep(d: float) -> None:
        delays.append(d)

    call = make_flaky_call(fail_times=3, exc=FakeHTTPError(500), then_return="OK")
    llm = LLMClient(
        call, max_retries=3, base_delay=1.0, max_delay=30.0, sleep_fn=record_sleep
    )
    llm.call()

    # Ожидаем [1, 2, 4]
    ok &= assert_eq(delays, [1.0, 2.0, 4.0], "задержки 1→2→4")
    return ok


def test_client_backoff_capped() -> bool:
    """Задержка не превышает max_delay."""
    ok = True

    delays: list[float] = []

    call = make_flaky_call(fail_times=3, exc=FakeHTTPError(500), then_return="OK")
    llm = LLMClient(
        call,
        max_retries=3,
        base_delay=10.0,
        max_delay=15.0,
        sleep_fn=lambda d: delays.append(d),
    )
    llm.call()

    # 10, min(20,15)=15, min(40,15)=15
    ok &= assert_eq(delays, [10.0, 15.0, 15.0], "задержки 10→15→15 (cap)")
    return ok


def test_client_callback_on_retry() -> bool:
    """Колбэк on_retry вызывается перед каждым сном."""
    ok = True
    events: list[tuple[int, float, str]] = []

    def on_retry(attempt: int, delay: float, err: LLMError) -> None:
        events.append((attempt, delay, type(err).__name__))

    call = make_flaky_call(fail_times=2, exc=FakeHTTPError(503), then_return="OK")
    llm = LLMClient(
        call, max_retries=3, base_delay=1.0, sleep_fn=noop_sleep, on_retry=on_retry
    )
    llm.call()

    ok &= assert_eq(len(events), 2, "колбэк вызван 2 раза")
    ok &= assert_eq(events[0][0], 0, "первый колбэк: attempt=0")
    ok &= assert_eq(events[1][0], 1, "второй колбэк: attempt=1")
    ok &= assert_eq(events[0][2], "LLMRetryableError", "тип в колбэке")
    return ok


def test_client_init_validation() -> bool:
    """Невалидные параметры → ValueError."""
    ok = True
    try:
        LLMClient(lambda: None, max_retries=-1)
        print("[FAIL] max_retries=-1 должен был упасть")
        ok = False
    except ValueError:
        print("[ ok ] max_retries=-1 → ValueError")

    try:
        LLMClient(lambda: None, base_delay=0)
        print("[FAIL] base_delay=0 должен был упасть")
        ok = False
    except ValueError:
        print("[ ok ] base_delay=0 → ValueError")

    try:
        LLMClient(lambda: None, base_delay=5, max_delay=1)
        print("[FAIL] max_delay < base_delay должен был упасть")
        ok = False
    except ValueError:
        print("[ ok ] max_delay < base_delay → ValueError")
    return ok


# ============================================================
# Main
# ============================================================

def main() -> None:
    all_ok = True

    print("--- Классификатор ---")
    all_ok &= test_classify()

    print("\n--- LLMClient ---")
    all_ok &= test_client_success_no_retry()
    all_ok &= test_client_retry_then_success()
    all_ok &= test_client_retry_exhausted()
    all_ok &= test_client_fatal_no_retry()
    all_ok &= test_client_timeout_retryable()
    all_ok &= test_client_backoff_increases()
    all_ok &= test_client_backoff_capped()
    all_ok &= test_client_callback_on_retry()
    all_ok &= test_client_init_validation()

    print()
    if all_ok:
        print("ВСЕ ТЕСТЫ ПРОШЛИ.")
    else:
        print("ЕСТЬ ПАДЕНИЯ, см. выше.")
        sys.exit(1)


if __name__ == "__main__":
    main()