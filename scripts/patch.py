# scripts/patch.py — PATCH_76: cloud_store на GitHub Gist
from __future__ import annotations
import ast, shutil, sys
from pathlib import Path

TAG = "PATCH_76"
ROOT = Path(__file__).resolve().parent.parent
if not (ROOT / "app.py").exists():
    print("[ERROR] app.py не найден.")
    sys.exit(1)

r = {"modified": [], "errors": []}

def _bk(p):
    b = p.with_suffix(p.suffix + ".bak_pre_" + TAG)
    if not b.exists() and p.exists():
        try:
            shutil.copy2(p, b)
        except Exception:
            pass


# ============================================================
# 1) persistence/cloud_store.py — на Gist
# ============================================================
CLOUD_STORE = '''"""persistence/cloud_store.py — облако через GitHub Gist.

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


def _save_gist(data: dict) -> bool:
    try:
        payload = {
            "files": {
                "wh40k_saves.json": {
                    "content": json.dumps(data, ensure_ascii=False, indent=2),
                }
            }
        }
        r = requests.patch(
            "https://api.github.com/gists/" + _GIST_ID,
            headers=_headers(),
            json=payload,
            timeout=15,
        )
        if r.status_code not in (200, 201):
            print("[cloud_store] PATCH fail: HTTP " + str(r.status_code)
                  + " " + r.text[:200])
            return False
        _CACHE["data"] = data
        _CACHE["ts"] = time.time()
        return True
    except Exception as e:
        print("[cloud_store] save error: " + type(e).__name__ + ": " + str(e))
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
'''

p = ROOT / "persistence" / "cloud_store.py"
_bk(p)
p.write_text(CLOUD_STORE, encoding="utf-8")
try:
    ast.parse(CLOUD_STORE)
    r["modified"].append("persistence/cloud_store.py — переписан под Gist")
except SyntaxError as e:
    r["errors"].append("cloud_store.py syntax: " + str(e))


# ============================================================
# 2) requirements.txt — requests
# ============================================================
p = ROOT / "requirements.txt"
text = p.read_text(encoding="utf-8")
if "requests" in text:
    r["modified"].append("requirements.txt — requests уже есть")
else:
    _bk(p)
    p.write_text(text.rstrip() + "\nrequests>=2.31.0\n", encoding="utf-8")
    r["modified"].append("requirements.txt — +requests")


print("=== PATCH " + TAG + " ===")
for m in r["modified"]:
    print("  [MODIFIED] " + m)
for e in r["errors"]:
    print("  [ERROR] " + e)
print("DONE" if not r["errors"] else "DONE (with errors)")