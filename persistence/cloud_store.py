"""persistence/cloud_store.py — облако через GitHub Gist.

Если GITHUB_GIST_ID и GITHUB_GIST_TOKEN заданы — используем Gist.
Если нет — локальные файлы.
"""
from __future__ import annotations
import json
import os
import time

import requests

_GIST_ID = None
_GIST_TOKEN = None
_CONFIGURED = None
_CACHE = {"data": None, "ts": 0.0}
_CACHE_TTL = 5.0


def _get_secret(key: str) -> str:
    val = os.environ.get(key, "").strip()
    if val:
        return val
    try:
        import streamlit as st
        val = str(st.secrets.get(key, "")).strip()
    except Exception:
        pass
    return val


def _ensure_config() -> bool:
    global _GIST_ID, _GIST_TOKEN, _CONFIGURED
    if _CONFIGURED is not None:
        return _CONFIGURED

    _GIST_ID = _get_secret("GITHUB_GIST_ID")
    _GIST_TOKEN = _get_secret("GITHUB_GIST_TOKEN")

    if not _GIST_ID or not _GIST_TOKEN:
        _CONFIGURED = False
        print("[cloud_store] Gist не настроен → локальные файлы")
        return False

    _CONFIGURED = True
    print("[cloud_store] GitHub Gist подключён: " + _GIST_ID[:8] + "...")
    return True


def is_configured() -> bool:
    return _ensure_config()


def _headers() -> dict:
    return {
        "Authorization": "token " + _GIST_TOKEN,
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _load_gist() -> dict:
    now = time.time()
    if _CACHE["data"] is not None and (now - _CACHE["ts"]) < _CACHE_TTL:
        return _CACHE["data"]

    try:
        r = requests.get(
            "https://api.github.com/gists/" + _GIST_ID,
            headers=_headers(),
            timeout=15,
        )
        if r.status_code != 200:
            print("[cloud_store] GET fail: HTTP " + str(r.status_code))
            return _CACHE["data"] or {}

        files = r.json().get("files", {}) or {}
        f = files.get("wh40k_saves.json") or {}
        content = f.get("content", "") or "{}"
        data = json.loads(content) if content.strip() else {}
        if not isinstance(data, dict):
            data = {}
        _CACHE["data"] = data
        _CACHE["ts"] = now
        return data
    except Exception as e:
        print("[cloud_store] load error: " + type(e).__name__ + ": " + str(e))
        return _CACHE["data"] or {}


def _save_gist(data: dict, retries: int = 3) -> bool:
    # PATCH_77: retry с backoff
    payload = {
        "files": {
            "wh40k_saves.json": {
                "content": json.dumps(data, ensure_ascii=False, indent=2),
            }
        }
    }
    last_err = None
    for attempt in range(retries):
        try:
            r = requests.patch(
                "https://api.github.com/gists/" + _GIST_ID,
                headers=_headers(),
                json=payload,
                timeout=15,
            )
            if r.status_code in (200, 201):
                _CACHE["data"] = data
                _CACHE["ts"] = time.time()
                return True

            # 5xx — retry, 4xx — нет
            if r.status_code >= 500:
                last_err = "HTTP " + str(r.status_code)
                print("[cloud_store] save attempt " + str(attempt + 1)
                      + " failed: " + last_err)
                time.sleep(1.0 * (attempt + 1))
                continue

            print("[cloud_store] PATCH fail: HTTP " + str(r.status_code)
                  + " " + r.text[:200])
            return False
        except requests.RequestException as e:
            last_err = type(e).__name__
            print("[cloud_store] save attempt " + str(attempt + 1)
                  + " exception: " + last_err)
            time.sleep(1.0 * (attempt + 1))

    print("[cloud_store] save failed after " + str(retries)
          + " attempts: " + str(last_err))
    return False


def hset_json(namespace: str, key: str, value) -> bool:
    if not _ensure_config():
        return False
    data = _load_gist()
    data.setdefault(namespace, {})[key] = value
    return _save_gist(data)


def hget_json(namespace: str, key: str):
    if not _ensure_config():
        return None
    data = _load_gist()
    ns = data.get(namespace, {}) or {}
    return ns.get(key)


def hkeys(namespace: str) -> list:
    if not _ensure_config():
        return []
    data = _load_gist()
    ns = data.get(namespace, {}) or {}
    return list(ns.keys())


def hdel(namespace: str, key: str) -> bool:
    if not _ensure_config():
        return False
    data = _load_gist()
    ns = data.get(namespace, {}) or {}
    if key in ns:
        del ns[key]
        return _save_gist(data)
    return True
