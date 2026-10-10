"""persistence/cloud_store.py — облачное хранилище (Upstash Redis).

Если UPSTASH_REDIS_REST_URL и UPSTASH_REDIS_REST_TOKEN заданы — используем
облако. Если нет — null-store, persistence/* работает с локальными файлами.
"""
from __future__ import annotations
import json
import os

_CLIENT = None
_CONFIGURED = None


def _get_client():
    global _CLIENT, _CONFIGURED
    if _CONFIGURED is not None:
        return _CLIENT

    url = os.environ.get("UPSTASH_REDIS_REST_URL", "").strip()
    token = os.environ.get("UPSTASH_REDIS_REST_TOKEN", "").strip()

    if not url or not token:
        try:
            import streamlit as st
            url = url or str(st.secrets.get("UPSTASH_REDIS_REST_URL", "")).strip()
            token = token or str(st.secrets.get("UPSTASH_REDIS_REST_TOKEN", "")).strip()
        except Exception:
            pass

    if not url or not token:
        _CONFIGURED = False
        _CLIENT = None
        print("[cloud_store] Upstash не настроен → локальные файлы")
        return None

    try:
        from upstash_redis import Redis
        _CLIENT = Redis(url=url, token=token)
        _CONFIGURED = True
        print("[cloud_store] Upstash подключён")
    except Exception as e:
        print("[cloud_store] Ошибка: " + type(e).__name__ + ": " + str(e))
        _CONFIGURED = False
        _CLIENT = None
    return _CLIENT


def is_configured() -> bool:
    return _get_client() is not None


def hset_json(namespace: str, key: str, value) -> bool:
    r = _get_client()
    if r is None:
        return False
    try:
        r.hset(namespace, key, json.dumps(value, ensure_ascii=False))
        return True
    except Exception as e:
        print("[cloud_store] hset fail: " + type(e).__name__)
        return False


def hget_json(namespace: str, key: str):
    r = _get_client()
    if r is None:
        return None
    try:
        raw = r.hget(namespace, key)
        if raw is None:
            return None
        return json.loads(raw)
    except Exception as e:
        print("[cloud_store] hget fail: " + type(e).__name__)
        return None


def hkeys(namespace: str) -> list:
    r = _get_client()
    if r is None:
        return []
    try:
        return list(r.hkeys(namespace) or [])
    except Exception:
        return []


def hdel(namespace: str, key: str) -> bool:
    r = _get_client()
    if r is None:
        return False
    try:
        r.hdel(namespace, key)
        return True
    except Exception:
        return False
