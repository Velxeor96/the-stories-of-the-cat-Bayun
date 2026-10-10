r"""Тесты core.llm_client и core.errors — чистый pytest.

Запуск:
    python -m pytest tests/test_llm_client.py -v
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest

from core.errors import (
    LLMFatalError,
    LLMRetryableError,
    classify_exception,
)
from core.llm_client import LLMClient


class FakeHTTPError(Exception):
    """Имитация ошибки SDK с .status_code (как у openai)."""
    def __init__(self, status_code: int, message: str = "fake error"):
        super().__init__(message)
        self.status_code = status_code


def noop_sleep(_: float) -> None:
    """Никаких пауз — для тестов backoff."""


def make_flaky_call(fail_times: int, exc: Exception, then_return: Any = "OK"):
    counter = {"n": 0}

    def _call(*args, **kwargs):
        if counter["n"] < fail_times:
            counter["n"] += 1
            raise exc
        return then_return

    _call.counter = counter
    return _call


# ============================================================
# classify_exception
# ============================================================

def test_classify_fatal_passthrough():
    assert isinstance(classify_exception(LLMFatalError("x")), LLMFatalError)


def test_classify_retryable_passthrough():
    assert isinstance(classify_exception(LLMRetryableError("x")), LLMRetryableError)


def test_classify_401_fatal():
    err = FakeHTTPError(401, "unauthorized")
    assert isinstance(classify_exception(err), LLMFatalError)


def test_classify_500_retryable():
    err = FakeHTTPError(500, "server error")
    assert isinstance(classify_exception(err), LLMRetryableError)


def test_classify_timeout_retryable():
    assert isinstance(
        classify_exception(Exception("Request timed out")),
        LLMRetryableError,
    )


# ============================================================
# LLMClient
# ============================================================

def test_client_success_no_retry():
    call = make_flaky_call(fail_times=0, exc=Exception("unused"), then_return="OK")
    llm = LLMClient(call, max_retries=3, sleep_fn=noop_sleep)
    assert llm.call() == "OK"
    assert call.counter["n"] == 0


def test_client_retry_then_success():
    call = make_flaky_call(fail_times=2, exc=FakeHTTPError(429), then_return="PONG")
    llm = LLMClient(call, max_retries=3, sleep_fn=noop_sleep)
    assert llm.call() == "PONG"
    assert call.counter["n"] == 2


def test_client_retry_exhausted():
    call = make_flaky_call(fail_times=10, exc=FakeHTTPError(429), then_return="NEVER")
    llm = LLMClient(call, max_retries=2, sleep_fn=noop_sleep)
    with pytest.raises(LLMRetryableError):
        llm.call()
    assert call.counter["n"] == 3


def test_client_fatal_no_retry():
    call = make_flaky_call(fail_times=10, exc=FakeHTTPError(401), then_return="NEVER")
    llm = LLMClient(call, max_retries=3, sleep_fn=noop_sleep)
    with pytest.raises(LLMFatalError):
        llm.call()
    assert call.counter["n"] == 1


def test_client_timeout_retryable():
    call = make_flaky_call(
        fail_times=1, exc=Exception("Request timed out"), then_return="OK"
    )
    llm = LLMClient(call, max_retries=2, sleep_fn=noop_sleep)
    assert llm.call() == "OK"
    assert call.counter["n"] == 1


def test_client_backoff_increases():
    delays: list[float] = []
    call = make_flaky_call(fail_times=3, exc=FakeHTTPError(500), then_return="OK")
    llm = LLMClient(
        call, max_retries=3, base_delay=1.0, max_delay=30.0,
        sleep_fn=delays.append,
    )
    llm.call()
    assert delays == [1.0, 2.0, 4.0]


def test_client_backoff_capped():
    delays: list[float] = []
    call = make_flaky_call(fail_times=3, exc=FakeHTTPError(500), then_return="OK")
    llm = LLMClient(
        call, max_retries=3, base_delay=10.0, max_delay=15.0,
        sleep_fn=delays.append,
    )
    llm.call()
    assert delays == [10.0, 15.0, 15.0]


def test_client_callback_on_retry():
    events: list[tuple[int, float, str]] = []

    def on_retry(attempt: int, delay: float, err: Exception) -> None:
        events.append((attempt, delay, type(err).__name__))

    call = make_flaky_call(fail_times=2, exc=FakeHTTPError(503), then_return="OK")
    llm = LLMClient(
        call, max_retries=3, base_delay=1.0, sleep_fn=noop_sleep, on_retry=on_retry,
    )
    llm.call()
    assert len(events) == 2
    assert [e[0] for e in events] == [0, 1]
    assert all(e[2] == "LLMRetryableError" for e in events)


def test_client_init_validation():
    call = make_flaky_call(fail_times=0, exc=Exception("x"))
    with pytest.raises(ValueError):
        LLMClient(call, max_retries=-1)
    with pytest.raises(ValueError):
        LLMClient(call, base_delay=0)
    with pytest.raises(ValueError):
        LLMClient(call, base_delay=10, max_delay=5)
