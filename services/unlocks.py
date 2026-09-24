# PATCH_15W
# services/unlocks.py — секретные коды доступа к уникальным темам.
from __future__ import annotations


ACCESS_CODES = {
    "АЛЬФА": [
        "tzeench", "khorn", "noorgl",
        "slaanesh", "inquisition", "gidra",
    ],
}


THEME_TITLES = {
    "khorn":       "Алчущий Крови",
    "tzeench":     "Повелитель Перемен",
    "slaanesh":    "Хранитель Секретов",
    "noorgl":      "Великий Нечистый",
    "inquisition": "Лорд-инквизитор",
    "gidra":       "Старший оперативник",
}


def verify_code(code):
    if not code:
        return []
    upper = str(code).strip().upper()
    if not upper:
        return []
    return list(ACCESS_CODES.get(upper, []))


def get_unlocked(login):
    if not login:
        return set()
    try:
        from persistence.settings import get_setting
        raw = get_setting(login, "unlocked_themes", "")
    except Exception as e:
        print("[unlocks] get fail: "
              + type(e).__name__ + ": " + str(e))
        return set()
    if not raw:
        return set()
    return set(x.strip() for x in str(raw).split(",") if x.strip())


def _save_unlocked(login, themes):
    try:
        from persistence.settings import set_setting
        set_setting(login, "unlocked_themes", ",".join(sorted(themes)))
        return True
    except Exception as e:
        print("[unlocks] save fail: "
              + type(e).__name__ + ": " + str(e))
        return False


def unlock(login, code):
    if not login:
        return (False, [], "Нет активной сессии.")
    themes = verify_code(code)
    if not themes:
        return (False, [], "Дух-машины отвергают сигнал. Протокол не распознан.")
    current = get_unlocked(login)
    new_themes = [t for t in themes if t not in current]
    merged = current | set(themes)
    if not _save_unlocked(login, merged):
        return (False, [], "Когитатор не отвечает. Попробуйте ещё раз.")
    if not new_themes:
        return (True, [], "Протокол уже активирован ранее.")
    return (True, new_themes,
            "Принято протоколов: " + str(len(new_themes)) + ".")


def title_for_theme(theme_key):
    if not theme_key:
        return ""
    return str(THEME_TITLES.get(str(theme_key), "") or "")
