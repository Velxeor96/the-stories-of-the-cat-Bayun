# scripts/hotfix_15y.py
# Создаёт services/progression.py и ui/screens/progression.py.
# Нужно, потому что PATCH_15L не был применён, а PATCH_15Y их импортирует.
# Запуск: python scripts\hotfix_15y.py
from __future__ import annotations

import ast
import shutil
import sys
from pathlib import Path

TAG = "HOTFIX_15Y"
ROOT = Path(__file__).resolve().parent.parent
FILES: dict = {}


FILES["services/progression.py"] = r"""# HOTFIX_15Y
# services/progression.py — правила прокачки Rogue Trader.
from __future__ import annotations


RANKS = [
    (0, "Ранг 1"), (2000, "Ранг 2"), (5000, "Ранг 3"),
    (9000, "Ранг 4"), (14000, "Ранг 5"), (20000, "Ранг 6"),
    (27000, "Ранг 7"), (35000, "Ранг 8"),
]

CHAR_COSTS = {
    "Simple":       [100, 250, 500],
    "Intermediate": [250, 500, 750],
    "Trained":      [500, 750, 1000],
    "Expert":       [750, 1000, 2500],
}

SKILL_COSTS = {"Trained": 100, "Experienced": 200, "Veteran": 300}
TALENT_COSTS = {"basic": 400, "prereq": 600, "universal": 750}

ARCHETYPE_CHARS = {
    "rogue_trader":  ["Fel", "Int", "Per"],
    "arch_militant": ["WS", "BS", "S", "T"],
    "astropath":     ["WP", "Per", "Int"],
    "explorator":    ["Int", "T", "Per"],
    "void_master":   ["Ag", "Int", "Per"],
    "missionary":    ["Fel", "WP", "S"],
    "navigator":     ["WP", "Int", "Per"],
    "seneschal":     ["Int", "Fel", "Per"],
}


def total_spent_xp(char):
    base = int(char.get("xp_spent_base", 0) or 0)
    extra = int(char.get("xp_spent", 0) or 0)
    return base + extra


def current_rank(char):
    spent = total_spent_xp(char)
    idx = 0
    for i, (threshold, _name) in enumerate(RANKS):
        if spent >= threshold:
            idx = i
    return idx + 1, RANKS[idx][1]


def rank_progress(char):
    spent = total_spent_xp(char)
    cur = 0
    nxt = None
    for threshold, _name in RANKS:
        if spent >= threshold:
            cur = threshold
        elif nxt is None:
            nxt = threshold
    if nxt is None:
        nxt = cur
    return spent, cur, nxt


def is_proficient(char, stat):
    arch = str(char.get("archetype_id") or char.get("archetype") or "").lower()
    lst = ARCHETYPE_CHARS.get(arch, [])
    return stat in lst


def char_advance_level(char, stat):
    adv = char.setdefault("advances", {})
    per = adv.setdefault(stat, {})
    return int(per.get("count", 0) or 0)


def char_advance_cost(char, stat):
    lvl = char_advance_level(char, stat)
    if lvl >= 3:
        return -1
    tier = "Simple" if is_proficient(char, stat) else "Expert"
    costs = CHAR_COSTS[tier]
    return costs[lvl]


def buy_char_advance(char, stat):
    cost = char_advance_cost(char, stat)
    if cost < 0:
        return False, "Характеристика уже на максимуме (+20)."
    if int(char.get("xp", 0) or 0) < cost:
        return False, "Недостаточно XP (нужно " + str(cost) + ")."
    char["xp"] = int(char.get("xp", 0)) - cost
    char["xp_spent"] = int(char.get("xp_spent", 0)) + cost
    chars = char.setdefault("characteristics", {})
    chars[stat] = int(chars.get(stat, 0)) + 5
    adv = char.setdefault("advances", {})
    per = adv.setdefault(stat, {})
    per["count"] = int(per.get("count", 0)) + 1
    return True, "+5 к " + stat + " за " + str(cost) + " XP."


def skill_cost(next_level):
    return SKILL_COSTS.get(next_level, 100)


def buy_skill(char, name):
    skills = char.setdefault("skills", [])
    found = None
    for s in skills:
        if isinstance(s, dict) and str(s.get("name")) == name:
            found = s
            break
        if isinstance(s, str) and s == name:
            found = {"name": s, "level": "Trained"}
            skills.remove(s)
            skills.append(found)
            break
    if found is None:
        cost = SKILL_COSTS["Trained"]
        if int(char.get("xp", 0)) < cost:
            return False, "Недостаточно XP (нужно " + str(cost) + ")."
        char["xp"] = int(char["xp"]) - cost
        char["xp_spent"] = int(char.get("xp_spent", 0)) + cost
        skills.append({"name": name, "level": "Trained"})
        return True, "Навык " + name + " (Trained) за " + str(cost) + " XP."
    level = str(found.get("level") or "Trained")
    order = ["Trained", "Experienced", "Veteran"]
    if level not in order:
        level = "Trained"
    idx = order.index(level)
    if idx >= len(order) - 1:
        return False, "Навык уже на максимуме (Veteran +20)."
    nxt = order[idx + 1]
    cost = SKILL_COSTS[nxt]
    if int(char.get("xp", 0)) < cost:
        return False, "Недостаточно XP (нужно " + str(cost) + ")."
    char["xp"] = int(char["xp"]) - cost
    char["xp_spent"] = int(char.get("xp_spent", 0)) + cost
    found["level"] = nxt
    return True, "Навык " + name + " -> " + nxt + " за " + str(cost) + " XP."


def buy_talent(char, name, cost):
    if int(char.get("xp", 0)) < cost:
        return False, "Недостаточно XP (нужно " + str(cost) + ")."
    tal = char.setdefault("talents", [])
    if any(str(t) == name for t in tal):
        return False, "Талант уже взят."
    char["xp"] = int(char["xp"]) - cost
    char["xp_spent"] = int(char.get("xp_spent", 0)) + cost
    tal.append(name)
    return True, "Талант " + name + " за " + str(cost) + " XP."


def buy_psy(char, name, cost):
    if int(char.get("psy_rating", 0) or 0) <= 0:
        return False, "Нет психорейтинга."
    if int(char.get("xp", 0)) < cost:
        return False, "Недостаточно XP (нужно " + str(cost) + ")."
    psy = char.setdefault("psychic_powers", [])
    if any(str(p) == name for p in psy):
        return False, "Техника уже известна."
    char["xp"] = int(char["xp"]) - cost
    char["xp_spent"] = int(char.get("xp_spent", 0)) + cost
    psy.append(name)
    return True, "Психосила " + name + " за " + str(cost) + " XP."


def available_psy_value(char):
    rank, _ = current_rank(char)
    if rank >= 6:
        return 400
    if rank >= 5:
        return 300
    if rank >= 3:
        return 200
    return 100
"""


FILES["ui/screens/progression.py"] = r"""# HOTFIX_15Y
# ui/screens/progression.py — экран «Развитие» (Rogue Trader).
from __future__ import annotations

import streamlit as st

from persistence.characters import load_character, save_character
from services import progression as P
from services.fallbacks import CHARACTERISTIC_NAMES


_CSS = '''<style>
.pg-head { text-align: center; padding: 8px 20px 4px 20px; }
.pg-title {
    font-family: Georgia, serif;
    font-size: 34px; letter-spacing: 5px;
    color: var(--fg);
    text-shadow: 0 0 22px var(--accent-glow);
    margin-bottom: 4px;
}
.pg-sub { color: var(--fg-dim); font-size: 13px; letter-spacing: 2px; }
.pg-rank {
    max-width: 620px; margin: 12px auto 18px auto;
    border: 1px solid var(--border);
    border-left: 3px solid var(--accent);
    border-radius: 6px;
    padding: 10px 16px;
    background: rgba(255,255,255,0.03);
    color: var(--fg);
}
.pg-rank .row {
    display: flex; justify-content: space-between;
    font-size: 13px; padding: 2px 0;
}
.pg-rank .lbl { color: var(--fg-dim); letter-spacing: 1px; }
.pg-rank .val { color: var(--fg); font-weight: 600; }
.pg-bar {
    height: 10px;
    background: rgba(255,255,255,0.06);
    border: 1px solid var(--border);
    border-radius: 4px; overflow: hidden;
    margin-top: 8px;
}
.pg-bar-fill {
    height: 100%;
    background: linear-gradient(90deg, var(--accent) 0%, var(--accent-soft) 100%);
    box-shadow: 0 0 10px var(--accent-glow);
}
.pg-char {
    display: flex; justify-content: space-between;
    border-bottom: 1px solid rgba(255,255,255,0.06);
    padding: 4px 0; font-size: 13px;
}
.pg-char .name { color: var(--fg); }
.pg-char .val { color: var(--accent-soft); font-weight: 600; }
.pg-char .note { color: var(--fg-dim); font-size: 11px; margin-left: 8px; }
</style>'''


def _login():
    return st.session_state.get("user_login") or ""


def _char_name():
    return st.session_state.get("active_character") or ""


def _load():
    lg, nm = _login(), _char_name()
    if not lg or not nm:
        return None
    try:
        return load_character(lg, nm)
    except Exception as e:
        st.error("Не удалось загрузить: " + type(e).__name__ + ": " + str(e))
        return None


def _save(char):
    try:
        save_character(_login(), _char_name(), char)
    except Exception as e:
        st.error("Не удалось сохранить: " + type(e).__name__ + ": " + str(e))


def render():
    st.markdown(_CSS, unsafe_allow_html=True)
    st.markdown(
        "<div class='pg-head'>"
        "<div class='pg-title'>РАЗВИТИЕ</div>"
        "<div class='pg-sub'>Rogue Trader · таблицы прогрессии</div>"
        "</div>",
        unsafe_allow_html=True,
    )

    char = _load()
    if not char:
        st.warning("Нет активного персонажа.")
        if st.button("В главное меню", key="pg_back_none"):
            st.session_state.screen = "main_menu"
            st.rerun()
        return

    _rank_block(char)

    tab_chars, tab_skills, tab_talents, tab_psy = st.tabs(
        ["Характеристики", "Навыки", "Таланты", "Психосилы"]
    )
    with tab_chars:
        _tab_chars(char)
    with tab_skills:
        _tab_skills(char)
    with tab_talents:
        _tab_talents(char)
    with tab_psy:
        _tab_psy(char)

    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("В игру", use_container_width=True, key="pg_to_game"):
            st.session_state.screen = "game"
            st.rerun()
    with c2:
        if st.button("В главное меню", use_container_width=True,
                     key="pg_to_menu"):
            st.session_state.screen = "main_menu"
            st.rerun()


def _rank_block(char):
    spent, cur, nxt = P.rank_progress(char)
    rank_num, rank_name = P.current_rank(char)
    free_xp = int(char.get("xp", 0) or 0)
    span = max(1, nxt - cur)
    pct = int(min(100, max(0, (spent - cur) * 100 / span)))
    html = (
        "<div class='pg-rank'>"
        "<div class='row'><span class='lbl'>РАНГ</span>"
        "<span class='val'>" + rank_name + "</span></div>"
        "<div class='row'><span class='lbl'>Потрачено XP</span>"
        "<span class='val'>" + str(spent) + "</span></div>"
        "<div class='row'><span class='lbl'>Свободно XP</span>"
        "<span class='val'>" + str(free_xp) + "</span></div>"
        "<div class='row'><span class='lbl'>Следующий ранг</span>"
        "<span class='val'>" + str(nxt) + " XP</span></div>"
        "<div class='pg-bar'><div class='pg-bar-fill' "
        "style='width:" + str(pct) + "%;'></div></div>"
        "</div>"
    )
    st.markdown(html, unsafe_allow_html=True)


def _tab_chars(char):
    stats = char.get("characteristics") or {}
    free = int(char.get("xp", 0) or 0)
    if not stats:
        st.caption("Характеристик нет.")
        return
    st.caption("Свободно XP: " + str(free))
    for stat, val in stats.items():
        name = CHARACTERISTIC_NAMES.get(stat, stat)
        lvl = P.char_advance_level(char, stat)
        cost = P.char_advance_cost(char, stat)
        prof = "профильная" if P.is_proficient(char, stat) else "элитная"
        note = "+" + str(lvl * 5) + " / +15 · " + prof
        c1, c2, c3 = st.columns([3, 2, 2])
        with c1:
            st.markdown(
                "<div class='pg-char'>"
                "<span class='name'>" + name + "</span>"
                "<span class='val'>" + str(val) + "</span>"
                "<span class='note'>" + note + "</span>"
                "</div>",
                unsafe_allow_html=True,
            )
        with c2:
            if cost < 0:
                st.caption("максимум")
            else:
                st.caption("цена: " + str(cost) + " XP")
        with c3:
            if cost >= 0:
                disabled = free < cost
                if st.button("+5", key="pg_char_" + stat,
                             disabled=disabled, use_container_width=True):
                    ok, msg = P.buy_char_advance(char, stat)
                    if ok:
                        _save(char)
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)


def _tab_skills(char):
    skills = char.get("skills") or []
    free = int(char.get("xp", 0) or 0)
    st.caption("Свободно XP: " + str(free))
    st.caption("Trained — 100 / Experienced — 200 / Veteran — 300")
    known = []
    for s in skills:
        if isinstance(s, dict):
            known.append(str(s.get("name")))
        else:
            known.append(str(s))
    if known:
        st.markdown("**Уже известные:**")
        for nm in known:
            lvl = "Trained"
            for s in skills:
                if isinstance(s, dict) and str(s.get("name")) == nm:
                    lvl = str(s.get("level") or "Trained")
            c1, c2 = st.columns([3, 2])
            with c1:
                st.write(nm + " (" + lvl + ")")
            with c2:
                order = ["Trained", "Experienced", "Veteran"]
                if lvl in order and order.index(lvl) < len(order) - 1:
                    nxt = order[order.index(lvl) + 1]
                    cst = P.skill_cost(nxt)
                    if st.button("-> " + nxt + " (" + str(cst) + ")",
                                 key="pg_sk_up_" + nm,
                                 disabled=free < cst,
                                 use_container_width=True):
                        ok, msg = P.buy_skill(char, nm)
                        if ok:
                            _save(char)
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)
                else:
                    st.caption("максимум")
    st.markdown("---")
    st.markdown("**Добавить новый навык:**")
    new_nm = st.text_input("Название", key="pg_sk_new")
    if st.button("Купить Trained (100 XP)", key="pg_sk_new_go",
                 disabled=not new_nm.strip() or free < 100):
        ok, msg = P.buy_skill(char, new_nm.strip())
        if ok:
            _save(char)
            st.success(msg)
            st.rerun()
        else:
            st.error(msg)


def _tab_talents(char):
    free = int(char.get("xp", 0) or 0)
    st.caption("Свободно XP: " + str(free))
    st.caption("Базовый — 400 / с пререквизитом — 600 / Universal — 750")
    tal = char.get("talents") or []
    if tal:
        st.markdown("**Взятые таланты:**")
        st.write(", ".join(str(t) for t in tal))
    else:
        st.caption("Талантов нет.")
    st.markdown("---")
    nm = st.text_input("Название таланта", key="pg_tal_new")
    kind = st.selectbox(
        "Тип",
        options=["basic", "prereq", "universal"],
        format_func=lambda k: {
            "basic": "Базовый (400 XP)",
            "prereq": "С пререквизитом (600 XP)",
            "universal": "Universal (750 XP)",
        }.get(k, k),
        key="pg_tal_kind",
    )
    cost = P.TALENT_COSTS[kind]
    if st.button("Взять (" + str(cost) + " XP)", key="pg_tal_go",
                 disabled=not nm.strip() or free < cost):
        ok, msg = P.buy_talent(char, nm.strip(), cost)
        if ok:
            _save(char)
            st.success(msg)
            st.rerun()
        else:
            st.error(msg)


def _tab_psy(char):
    psy_rating = int(char.get("psy_rating", 0) or 0)
    if psy_rating <= 0:
        st.info("Персонаж не псайкер (PSY = 0).")
        return
    free = int(char.get("xp", 0) or 0)
    max_val = P.available_psy_value(char)
    st.caption("PSY: " + str(psy_rating) + " · свободно XP: " + str(free))
    st.caption("Максимальное Value по рангу: " + str(max_val))
    powers = char.get("psychic_powers") or []
    if powers:
        st.markdown("**Известные техники:**")
        st.write(", ".join(str(p) for p in powers))
    else:
        st.caption("Психосил нет.")
    st.markdown("---")
    nm = st.text_input("Название техники", key="pg_psy_new")
    val = st.selectbox(
        "Value",
        options=[200, 300, 400],
        index=0,
        format_func=lambda v: str(v) + " XP",
        key="pg_psy_val",
    )
    if val > max_val:
        st.warning("Rank too low для Value " + str(val) + ".")
    if st.button("Изучить (" + str(val) + " XP)", key="pg_psy_go",
                 disabled=not nm.strip() or free < val or val > max_val):
        ok, msg = P.buy_psy(char, nm.strip(), val)
        if ok:
            _save(char)
            st.success(msg)
            st.rerun()
        else:
            st.error(msg)
"""


def _write_one(rel_path, content):
    dst = ROOT / rel_path
    dst.parent.mkdir(parents=True, exist_ok=True)
    existed = dst.exists()
    if existed:
        try:
            old = dst.read_text(encoding="utf-8")
        except Exception as e:
            return "ERROR reading: " + type(e).__name__ + ": " + str(e)
        if old == content:
            return "skip (identical)"
    if dst.suffix == ".py":
        try:
            ast.parse(content)
        except SyntaxError as e:
            return ("ERROR SyntaxError: line " + str(e.lineno)
                    + ": " + str(e.msg))
    if existed:
        bak = dst.with_name(dst.name + ".bak_pre_" + TAG)
        try:
            shutil.copy2(dst, bak)
        except Exception as e:
            return "ERROR backup: " + type(e).__name__ + ": " + str(e)
    try:
        dst.write_text(content, encoding="utf-8")
    except Exception as e:
        return "ERROR write: " + type(e).__name__ + ": " + str(e)
    return "backup + overwrite" if existed else "create"


def main():
    print("=" * 64)
    print("HOTFIX " + TAG + " — создать progression модули")
    print("ROOT: " + str(ROOT))
    print("=" * 64)
    any_error = False
    for rel in FILES:
        status = _write_one(rel, FILES[rel])
        if status.startswith("ERROR"):
            any_error = True
        print("  " + rel.ljust(34) + " -> " + status)
    print("=" * 64)
    print("DONE" + (" (with errors)" if any_error else " — ok"))
    return 1 if any_error else 0


if __name__ == "__main__":
    sys.exit(main())