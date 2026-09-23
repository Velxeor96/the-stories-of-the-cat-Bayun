# PATCH_15N
# ui/version_info.py — чтение VERSION и CHANGELOG.md.
from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def get_current_version() -> str:
    p = _ROOT / "VERSION"
    if not p.exists():
        return "0.0.0"
    try:
        txt = p.read_text(encoding="utf-8").strip()
        return txt.splitlines()[0].strip() if txt else "0.0.0"
    except Exception:
        return "0.0.0"


def get_changelog() -> str:
    p = _ROOT / "CHANGELOG.md"
    if not p.exists():
        return ""
    try:
        return p.read_text(encoding="utf-8")
    except Exception:
        return ""


def get_changelog_top() -> str:
    text = get_changelog()
    if not text:
        return ""
    lines = text.splitlines()
    out = []
    started = False
    for line in lines:
        if line.startswith("## ["):
            if started:
                break
            started = True
            out.append(line)
            continue
        if started:
            out.append(line)
    return "\n".join(out).strip()


def mark_version_seen(login: str) -> None:
    if not login:
        return
    try:
        from persistence.settings import set_setting
        set_setting(login, "seen_version", get_current_version())
    except Exception as e:
        print("[version_info] mark_version_seen fail: "
              + type(e).__name__ + ": " + str(e))


def has_seen_current(login: str) -> bool:
    if not login:
        return False
    try:
        from persistence.settings import get_setting
        seen = str(get_setting(login, "seen_version", "") or "")
    except Exception:
        seen = ""
    return seen == get_current_version()
