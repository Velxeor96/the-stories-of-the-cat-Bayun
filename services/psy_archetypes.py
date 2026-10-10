"""services/psy_archetypes.py — авто-определение psy_rating по архетипу.

PATCH_83: если у персонажа не задан psy_rating, а архетип — псайкерский,
проставляем psy_rating автоматически.
"""
from __future__ import annotations


# Архетип → psy_rating. Ключи в нижнем регистре.
PSY_ARCHETYPES = {
    # Империум
    "astropath": 5,
    "астропат": 5,
    "sanctioned psyker": 4,
    "санкционированный псайкер": 4,
    "primaris psyker": 4,
    "примарис псайкер": 4,
    "librarian": 4,
    "библиарий": 4,
    "inquisitor psyker": 4,
    "инквизитор-псайкер": 4,
    "inquisitor_psyker": 4,
    "navigator": 5,
    "навигатор": 5,
    # Хаос
    "sorcerer": 5,
    "сорцерер": 5,
    "колдун": 5,
    "chaos sorcerer": 5,
    "dark apostle": 2,
    "тёмный апостол": 2,
    # Эльдар
    "farseer": 7,
    "фарсир": 7,
    "warlock": 5,
    "варлок": 5,
    "spiritseer": 5,
    "спиритсир": 5,
    "shadowseer": 5,
    "теневой провидец": 5,
    "bonesinger": 4,
    "костопев": 4,
    # Тираниды
    "zoanthrope": 5,
    "зоантроп": 5,
    "neurothrope": 6,
    "невротроп": 6,
    "broodlord": 3,
    "владыка выводка": 3,
    "hive tyrant": 5,
    "тиран улья": 5,
    # Орки
    "weirdboy": 5,
    "вирдбой": 5,
    "wurrboy": 5,
    "вуррбой": 5,
}


def _norm(s) -> str:
    return str(s or "").lower().replace("_", " ").replace("-", " ").strip()


def detect_psy_rating(char: dict) -> int:
    """Определяет psy_rating по архетипу. 0 — не псайкер."""
    if not isinstance(char, dict):
        return 0

    # Явно заданный > 0 — уважаем
    explicit = char.get("psy_rating")
    if explicit is not None:
        try:
            v = int(explicit)
            if v > 0:
                return v
        except (ValueError, TypeError):
            pass

    cid = _norm(char.get("career_id", ""))
    cname = _norm(char.get("career_name", ""))
    aid = _norm(char.get("archetype_id", ""))
    aname = _norm(char.get("archetype_name", ""))

    for key in (cid, aid, cname, aname):
        if key and key in PSY_ARCHETYPES:
            return PSY_ARCHETYPES[key]

    # Подстрочный поиск
    for src in (cid, aid, cname, aname):
        if not src:
            continue
        for key, val in PSY_ARCHETYPES.items():
            if key and key in src:
                return val

    return 0


def ensure_psy_fields(char: dict) -> None:
    """Инициализирует поля психосил, если их нет."""
    if not isinstance(char, dict):
        return
    rating = detect_psy_rating(char)
    if rating > 0 and not int(char.get("psy_rating", 0) or 0):
        char["psy_rating"] = rating
    cur_rating = int(char.get("psy_rating", 0) or 0)
    if char.get("psy_charge") is None:
        char["psy_charge"] = cur_rating * 3
    if "corruption" not in char:
        char["corruption"] = 0
    if "insanity" not in char:
        char["insanity"] = 0
    fid = str(char.get("faction_id", "")).lower()
    if fid == "chaos" and not isinstance(char.get("chaos_god_favor"), dict):
        char["chaos_god_favor"] = {}
