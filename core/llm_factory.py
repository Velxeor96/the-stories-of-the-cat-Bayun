# PATCH_15I
# core/llm_factory.py — фабрика LLM-клиентов (OpenAI-совместимые + GigaChat).
from __future__ import annotations

import os
import time
import uuid
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import requests

_ROOT = Path(__file__).resolve().parents[1]

_SSL_CACHE: dict[str, Any] = {"value": None}


def _read_ssl_setting() -> str | None:
    p = _ROOT / ".streamlit" / "secrets.toml"
    if not p.exists():
        return None
    try:
        import tomllib
    except ImportError:
        return None
    try:
        with p.open("rb") as f:
            data = tomllib.load(f)
        v = data.get("GIGACHAT_VERIFY_SSL")
        return str(v) if v is not None else None
    except Exception:
        return None


def _ssl_verify() -> Any:
    if _SSL_CACHE["value"] is not None:
        return _SSL_CACHE["value"]

    val = os.environ.get("GIGACHAT_VERIFY_SSL")
    if val is None:
        val = _read_ssl_setting()
    if val is None:
        val = "1"
    low = str(val).strip().lower()

    if low in ("0", "false", "no", "off"):
        result: Any = False
    elif low in ("1", "true", "yes", "on", ""):
        result = True
    else:
        p = Path(val)
        if not p.is_absolute():
            p = _ROOT / val
        if not p.exists():
            raise RuntimeError("GIGACHAT_VERIFY_SSL: файл не найден: " + str(p))
        result = str(p)

    _SSL_CACHE["value"] = result
    return result


_GIGA_OAUTH_URL = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
_GIGA_SCOPE = "GIGACHAT_API_PERS"
_GIGA_TOKEN: dict[str, Any] = {"access_token": None, "expires_at": 0.0}

_GIGA_CONNECT_TIMEOUT = 10
_GIGA_OAUTH_READ_TIMEOUT = 30
_GIGA_CHAT_READ_TIMEOUT = 120


def _gigachat_get_token(credentials: str) -> str:
    if not credentials:
        raise RuntimeError("GigaChat: пустой ключ")
    now = time.time()
    if _GIGA_TOKEN["access_token"] and _GIGA_TOKEN["expires_at"] - now > 60:
        return _GIGA_TOKEN["access_token"]

    headers = {
        "Authorization": "Basic " + credentials,
        "RqUID": str(uuid.uuid4()),
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
    }
    t0 = time.time()
    print("[gigachat] OAuth: requesting token (connect="
          + str(_GIGA_CONNECT_TIMEOUT) + "s, read="
          + str(_GIGA_OAUTH_READ_TIMEOUT) + "s)...")
    try:
        resp = requests.post(
            _GIGA_OAUTH_URL, headers=headers, data={"scope": _GIGA_SCOPE},
            timeout=(_GIGA_CONNECT_TIMEOUT, _GIGA_OAUTH_READ_TIMEOUT),
            verify=_ssl_verify(),
        )
    except requests.exceptions.Timeout as e:
        print("[gigachat] OAuth TIMEOUT after "
              + format(time.time() - t0, ".2f") + "s: " + str(e))
        raise
    except requests.exceptions.RequestException as e:
        print("[gigachat] OAuth NETWORK ERROR after "
              + format(time.time() - t0, ".2f") + "s: "
              + type(e).__name__ + ": " + str(e))
        raise
    dt = time.time() - t0
    print("[gigachat] OAuth: HTTP " + str(resp.status_code)
          + " in " + format(dt, ".2f") + "s")
    if not resp.ok:
        raise RuntimeError("GigaChat OAuth HTTP " + str(resp.status_code)
                           + ": " + resp.text[:300])
    data = resp.json()
    token = data.get("access_token")
    if not token:
        raise RuntimeError("GigaChat OAuth: нет access_token: " + str(data))
    exp = data.get("expires_at")
    _GIGA_TOKEN["expires_at"] = (
        float(exp) / 1000.0 if isinstance(exp, (int, float)) else now + 1500
    )
    _GIGA_TOKEN["access_token"] = token
    return token


class _GigaMessage:
    def __init__(self, content: str):
        self.content = content
        self.role = "assistant"


class _GigaChoice:
    def __init__(self, content: str):
        self.message = _GigaMessage(content)
        self.finish_reason = "stop"
        self.index = 0


class _GigaResponse:
    def __init__(self, raw: dict):
        content = ""
        choices = raw.get("choices") or []
        if choices:
            content = (choices[0].get("message") or {}).get("content") or ""
        self.choices = [_GigaChoice(content)]
        self.raw = raw


class _GigaCompletions:
    def __init__(self, credentials: str, base_url: str):
        self._credentials = credentials
        self._base_url = base_url.rstrip("/")

    def create(self, *, model: str, messages: list,
               temperature: float = 0.7, max_tokens: int = 2000, **kwargs):
        token = _gigachat_get_token(self._credentials)
        url = self._base_url + "/chat/completions"
        headers = {
            "Authorization": "Bearer " + token,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        body = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        t0 = time.time()
        print("[gigachat] POST /chat/completions model=" + str(model)
              + " msgs=" + str(len(messages))
              + " (connect=" + str(_GIGA_CONNECT_TIMEOUT)
              + "s, read=" + str(_GIGA_CHAT_READ_TIMEOUT) + "s)...")
        try:
            resp = requests.post(
                url, headers=headers, json=body,
                timeout=(_GIGA_CONNECT_TIMEOUT, _GIGA_CHAT_READ_TIMEOUT),
                verify=_ssl_verify(),
            )
        except requests.exceptions.Timeout as e:
            print("[gigachat] CHAT TIMEOUT after "
                  + format(time.time() - t0, ".2f") + "s: " + str(e))
            raise
        except requests.exceptions.RequestException as e:
            print("[gigachat] CHAT NETWORK ERROR after "
                  + format(time.time() - t0, ".2f") + "s: "
                  + type(e).__name__ + ": " + str(e))
            raise
        dt = time.time() - t0
        body_preview = (resp.text or "")[:200].replace("\n", " ")
        print("[gigachat] CHAT: HTTP " + str(resp.status_code)
              + " in " + format(dt, ".2f") + "s; body[:200]=" + body_preview)
        if not resp.ok:
            raise RuntimeError("GigaChat HTTP " + str(resp.status_code)
                               + ": " + resp.text[:300])
        return _GigaResponse(resp.json())


class _GigaChat:
    def __init__(self, credentials: str, base_url: str):
        self.chat = SimpleNamespace(
            completions=_GigaCompletions(credentials, base_url)
        )


def make_client(provider_key: str, api_key: str, base_url: str):
    if provider_key == "gigachat":
        return _GigaChat(credentials=api_key, base_url=base_url)
    try:
        from openai import OpenAI
    except ImportError as e:
        raise RuntimeError("pip install openai") from e
    return OpenAI(api_key=api_key, base_url=base_url)
