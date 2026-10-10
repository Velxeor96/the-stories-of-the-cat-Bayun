# scripts/patch.py — PATCH_87: fix subfaction resolution + character screen + psy sidebar
from __future__ import annotations
import ast, re, shutil, sys
from pathlib import Path

TAG = "PATCH_87"
ROOT = Path(__file__).resolve().parent.parent
if not (ROOT / "app.py").exists():
    print("[ERROR] app.py не найден.")
    sys.exit(1)

r = {"modified": [], "errors": [], "warns": []}


def _bk(p):
    b = p.with_suffix(p.suffix + ".bak_pre_" + TAG)
    if not b.exists() and p.exists():
        try:
            shutil.copy2(p, b)
        except Exception:
            pass


def _write(rel, txt):
    p = ROOT / rel
    _bk(p)
    try:
        ast.parse(txt)
    except SyntaxError as e:
        r["errors"].append(rel + " syntax: " + str(e) + " (line " + str(e.lineno) + ")")
        return False
    p.write_text(txt, encoding="utf-8")
    r["modified"].append(rel)
    return True


# ============================================================
# 1) services/fallbacks.py — resolve subfaction -> parent faction
# ============================================================
def _patch_fallbacks():
    p = ROOT / "services" / "fallbacks.py"
    txt = p.read_text(encoding="utf-8")
    orig = txt
    notes = []

    # 1.1) Добавить helper _resolve_parent_faction после блока SUBFACTION_NAMES
    if "_resolve_parent_faction" not in txt:
        # Вставим helper перед первым def _loader_hw
        marker = "def _loader_hw(faction_id):"
        if marker in txt:
            helper = '''def _resolve_parent_faction(fid: str) -> str:
    """PATCH_87: subfaction -> родительская faction. Пример:
    'rogue_trader' -> 'imperium', 'asuryani' -> 'eldar'.
    Если fid уже faction или неизвестен — возвращает как есть."""
    if not fid:
        return fid
    try:
        if fid in FACTIONS:
            return fid
        for parent, data in FACTIONS.items():
            subs = data.get("subfactions") or []
            if fid in subs:
                return parent
    except Exception:
        pass
    return fid


'''
            txt = txt.replace(marker, helper + marker, 1)
            notes.append("_resolve_parent_faction добавлен")
        else:
            notes.append("НЕ нашёл _loader_hw — helper не вставлен")

    # 1.2) Заменить home_worlds_for
    old_hw = '''def home_worlds_for(faction_id: str) -> list:
    ids = _loader_hw(faction_id)
    if ids:
        return ids
    if faction_id == "eldar":
        return list(ELDAR_CRAFTWORLDS.keys())
    out = []
    for key, data in HOME_WORLDS.items():
        allowed = data.get("allowed_factions") or []
        if not allowed or faction_id in allowed:
            out.append(key)
    return out'''
    new_hw = '''def home_worlds_for(faction_id: str) -> list:
    """PATCH_87: сначала пробуем subfaction-specific, потом родительскую."""
    resolved = _resolve_parent_faction(faction_id)
    tried = [faction_id] if faction_id == resolved else [faction_id, resolved]
    for fid in tried:
        ids = _loader_hw(fid)
        if ids:
            return ids
    if resolved == "eldar":
        return list(ELDAR_CRAFTWORLDS.keys())
    out = []
    for key, data in HOME_WORLDS.items():
        allowed = data.get("allowed_factions") or []
        if not allowed or resolved in allowed:
            out.append(key)
    return out'''
    if old_hw in txt:
        txt = txt.replace(old_hw, new_hw, 1)
        notes.append("home_worlds_for обновлён")
    else:
        notes.append("НЕ нашёл home_worlds_for")

    # 1.3) Заменить careers_for
    old_cr = '''def careers_for(faction_id: str) -> list:
    ids = _loader_careers(faction_id)
    if ids:
        return ids
    if faction_id == "eldar":
        return list(ELDAR_PATHS.keys())
    out = []
    for key, data in CAREERS.items():
        allowed = data.get("allowed_factions") or []
        if not allowed or faction_id in allowed:
            out.append(key)
    return out'''
    new_cr = '''def careers_for(faction_id: str) -> list:
    """PATCH_87: сначала subfaction-specific, потом родительская."""
    resolved = _resolve_parent_faction(faction_id)
    tried = [faction_id] if faction_id == resolved else [faction_id, resolved]
    for fid in tried:
        ids = _loader_careers(fid)
        if ids:
            return ids
    if resolved == "eldar":
        return list(ELDAR_PATHS.keys())
    out = []
    for key, data in CAREERS.items():
        allowed = data.get("allowed_factions") or []
        if not allowed or resolved in allowed:
            out.append(key)
    return out'''
    if old_cr in txt:
        txt = txt.replace(old_cr, new_cr, 1)
        notes.append("careers_for обновлён")
    else:
        notes.append("НЕ нашёл careers_for")

    # 1.4) home_world_display_name — resolve
    old_hwdn = '''def home_world_display_name(faction_id: str, key: str) -> str:
    if faction_id == "eldar" and key in ELDAR_CRAFTWORLDS:
        return ELDAR_CRAFTWORLDS[key]["name"]
    try:
        from services.data_loader import get_home_world
        d = get_home_world(faction_id, key)
        if d and d.get("name"):
            return d["name"]
    except Exception:
        pass
    if key in HOME_WORLDS:
        return HOME_WORLDS[key].get("name", key)
    return key'''
    new_hwdn = '''def home_world_display_name(faction_id: str, key: str) -> str:
    resolved = _resolve_parent_faction(faction_id)
    if resolved == "eldar" and key in ELDAR_CRAFTWORLDS:
        return ELDAR_CRAFTWORLDS[key]["name"]
    for fid in ([faction_id] if faction_id == resolved else [faction_id, resolved]):
        try:
            from services.data_loader import get_home_world
            d = get_home_world(fid, key)
            if d and d.get("name"):
                return d["name"]
        except Exception:
            pass
    if key in HOME_WORLDS:
        return HOME_WORLDS[key].get("name", key)
    return key'''
    if old_hwdn in txt:
        txt = txt.replace(old_hwdn, new_hwdn, 1)
        notes.append("home_world_display_name обновлён")
    else:
        notes.append("НЕ нашёл home_world_display_name")

    # 1.5) career_display_name — resolve
    old_cdn = '''def career_display_name(faction_id: str, key: str) -> str:
    if faction_id == "eldar" and key in ELDAR_PATHS:
        return ELDAR_PATHS[key]["name"]
    try:
        from services.data_loader import get_career
        d = get_career(faction_id, key)
        if d and d.get("name"):
            return d["name"]
    except Exception:
        pass
    if key in CAREERS:
        return CAREERS[key].get("name", key)
    return key'''
    new_cdn = '''def career_display_name(faction_id: str, key: str) -> str:
    resolved = _resolve_parent_faction(faction_id)
    if resolved == "eldar" and key in ELDAR_PATHS:
        return ELDAR_PATHS[key]["name"]
    for fid in ([faction_id] if faction_id == resolved else [faction_id, resolved]):
        try:
            from services.data_loader import get_career
            d = get_career(fid, key)
            if d and d.get("name"):
                return d["name"]
        except Exception:
            pass
    if key in CAREERS:
        return CAREERS[key].get("name", key)
    return key'''
    if old_cdn in txt:
        txt = txt.replace(old_cdn, new_cdn, 1)
        notes.append("career_display_name обновлён")
    else:
        notes.append("НЕ нашёл career_display_name")

    # 1.6) home_world_data — resolve
    old_hwd = '''def home_world_data(faction_id: str, key: str) -> dict:
    if faction_id == "eldar" and key in ELDAR_CRAFTWORLDS:
        d = dict(ELDAR_CRAFTWORLDS[key])
        d["id"] = key
        return d
    if key in HOME_WORLDS:
        d = dict(HOME_WORLDS[key])
        d["id"] = key
        return d
    try:
        from services.data_loader import get_home_world
        d = get_home_world(faction_id, key)
        if d:
            d["id"] = key
            return d
    except Exception:
        pass
    return {}'''
    new_hwd = '''def home_world_data(faction_id: str, key: str) -> dict:
    resolved = _resolve_parent_faction(faction_id)
    if resolved == "eldar" and key in ELDAR_CRAFTWORLDS:
        d = dict(ELDAR_CRAFTWORLDS[key])
        d["id"] = key
        return d
    for fid in ([faction_id] if faction_id == resolved else [faction_id, resolved]):
        try:
            from services.data_loader import get_home_world
            d = get_home_world(fid, key)
            if d:
                d["id"] = key
                return d
        except Exception:
            pass
    if key in HOME_WORLDS:
        d = dict(HOME_WORLDS[key])
        d["id"] = key
        return d
    return {}'''
    if old_hwd in txt:
        txt = txt.replace(old_hwd, new_hwd, 1)
        notes.append("home_world_data обновлён")
    else:
        notes.append("НЕ нашёл home_world_data")

    # 1.7) career_data — resolve
    old_cd = '''def career_data(faction_id: str, key: str) -> dict:
    if faction_id == "eldar" and key in ELDAR_PATHS:
        d = dict(ELDAR_PATHS[key])
        d["id"] = key
        return d
    if key in CAREERS:
        d = dict(CAREERS[key])
        d["id"] = key
        return d
    try:
        from services.data_loader import get_career
        d = get_career(faction_id, key)
        if d:
            d["id"] = key
            return d
    except Exception:
        pass
    return {}'''
    new_cd = '''def career_data(faction_id: str, key: str) -> dict:
    resolved = _resolve_parent_faction(faction_id)
    if resolved == "eldar" and key in ELDAR_PATHS:
        d = dict(ELDAR_PATHS[key])
        d["id"] = key
        return d
    for fid in ([faction_id] if faction_id == resolved else [faction_id, resolved]):
        try:
            from services.data_loader import get_career
            d = get_career(fid, key)
            if d:
                d["id"] = key
                return d
        except Exception:
            pass
    if key in CAREERS:
        d = dict(CAREERS[key])
        d["id"] = key
        return d
    return {}'''
    if old_cd in txt:
        txt = txt.replace(old_cd, new_cd, 1)
        notes.append("career_data обновлён")
    else:
        notes.append("НЕ нашёл career_data")

    if txt != orig:
        if _write("services/fallbacks.py", txt):
            r["warns"].extend(["fallbacks.py: " + n for n in notes])


_patch_fallbacks()


# ============================================================
# 2) services/character_creation.py — ensure_psy_fields в build_character
# ============================================================
def _patch_character_creation():
    p = ROOT / "services" / "character_creation.py"
    txt = p.read_text(encoding="utf-8")
    orig = txt

    # Заменить "return {  # PATCH_59: has_ship" на "char = {  # PATCH_59"
    # и добавить в конце ensure_psy_fields
    old_head = "    return {  # PATCH_59: has_ship"
    new_head = "    char = {  # PATCH_59: has_ship"
    if old_head in txt:
        txt = txt.replace(old_head, new_head, 1)
    elif "    char = {  # PATCH_59" in txt:
        pass
    else:
        r["warns"].append("character_creation: не нашёл 'return {  # PATCH_59'")
        return

    # Финальный закрывающий "}" — конец dict. Ищем по маркеру
    # "tyranid_traits": faction_traits if faction_id == "tyranids" else [],
    # и добавляем после него ensure_psy_fields + return char
    marker = (
        '        "tyranid_traits": faction_traits if faction_id == "tyranids" else [],\n'
        "    }"
    )
    new_tail = (
        '        "tyranid_traits": faction_traits if faction_id == "tyranids" else [],\n'
        "    }\n"
        "\n"
        "    # PATCH_87: авто-инициализация психосил по архетипу\n"
        "    try:\n"
        "        from services.psy_archetypes import ensure_psy_fields\n"
        "        ensure_psy_fields(char)\n"
        "        # Если у псайкера есть psy_rating, но не заданы силы —\n"
        "        # дадим стартовый набор доступных ему сил.\n"
        "        _pr = int(char.get(\"psy_rating\", 0) or 0)\n"
        "        if _pr > 0 and not char.get(\"psychic_powers\"):\n"
        "            try:\n"
        "                from services import psychic as _psy\n"
        "                _powers = _psy.get_powers(char) or []\n"
        "                char[\"psychic_powers\"] = list(_powers)[:5]\n"
        "                char[\"psy_charge\"] = _pr * 3\n"
        "            except Exception as _e:\n"
        "                print(\"[creation] psy powers: \" + type(_e).__name__)\n"
        "    except Exception as _e:\n"
        "        print(\"[creation] ensure_psy_fields: \" + type(_e).__name__)\n"
        "\n"
        "    return char"
    )
    if marker in txt:
        txt = txt.replace(marker, new_tail, 1)
    else:
        r["warns"].append("character_creation: не нашёл конец dict с tyranid_traits")
        return

    if txt != orig:
        if _write("services/character_creation.py", txt):
            r["warns"].append("character_creation.py: ensure_psy_fields добавлен")


_patch_character_creation()


# ============================================================
# 3) app.py — character в SCREENS + удалить _draw_psy_sidebar_button
# ============================================================
def _patch_app():
    p = ROOT / "app.py"
    txt = p.read_text(encoding="utf-8")
    orig = txt
    notes = []

    # 3.1) Добавить "character": character.render в SCREENS если нет
    if '"character": character.render' not in txt:
        # Найдём закрытие SCREENS
        m = re.search(r"SCREENS\s*=\s*\{", txt)
        if m:
            start = m.end() - 1
            depth = 0
            i = start
            end = None
            while i < len(txt):
                if txt[i] == "{":
                    depth += 1
                elif txt[i] == "}":
                    depth -= 1
                    if depth == 0:
                        end = i
                        break
                i += 1
            if end is not None:
                block = txt[start:end + 1]
                lines = block.rstrip().rstrip("}").rstrip().split("\n")
                indent = "    "
                if lines:
                    last = lines[-1]
                    m2 = re.match(r"^(\s*)", last)
                    if m2:
                        indent = m2.group(1) or "    "
                new_block = (
                    block.rstrip().rstrip("}").rstrip()
                    + "\n"
                    + indent + '"character": character.render,\n'
                    + "}"
                )
                txt = txt[:start] + new_block + txt[end + 1:]
                notes.append("character добавлен в SCREENS")
            else:
                notes.append("НЕ нашёл закрывающую } SCREENS")
        else:
            notes.append("НЕ нашёл SCREENS")
    else:
        notes.append("character уже в SCREENS")

    # 3.2) Удалить _draw_psy_sidebar_button (helper + вызов)
    helper_pat = re.compile(
        r"\n# PATCH_84:.*?_draw_psy_sidebar_button\(\):.*?"
        r"print\(\"\[app\] psy sidebar: \" \+ str\(e\)\)\s*",
        re.DOTALL,
    )
    if helper_pat.search(txt):
        txt = helper_pat.sub("\n", txt, count=1)
        notes.append("_draw_psy_sidebar_button удалён")
    elif "_draw_psy_sidebar_button" in txt:
        # Fallback: простая замена блока
        lines = txt.split("\n")
        new_lines = []
        skip = 0
        for i, line in enumerate(lines):
            if skip > 0:
                skip -= 1
                continue
            if "_draw_psy_sidebar_button" in line and "def " in line:
                # пропускаем до отступа меньше 4 или пустой строки с новым def
                j = i
                while j < len(lines):
                    l = lines[j]
                    if j > i and l and not l.startswith(" ") and not l.startswith("\t"):
                        break
                    j += 1
                skip = j - i - 1
                continue
            if "_draw_psy_sidebar_button()" in line and "def " not in line:
                continue  # удалить вызов
            new_lines.append(line)
        txt = "\n".join(new_lines)
        notes.append("_draw_psy_sidebar_button удалён (fallback)")
    else:
        notes.append("helper не найден (уже удалён?)")

    # 3.3) Если остался вызов — убрать
    txt = re.sub(r"\n\s*_draw_psy_sidebar_button\(\)\s*\n", "\n", txt)

    if txt != orig:
        if _write("app.py", txt):
            r["warns"].extend(["app.py: " + n for n in notes])
    else:
        r["warns"].append("app.py: без изменений")


_patch_app()


# ============================================================
# 4) ui/screens/game.py — кнопка 🔮 перед кнопкой Бой
# ============================================================
def _patch_game():
    p = ROOT / "ui" / "screens" / "game.py"
    txt = p.read_text(encoding="utf-8")
    orig = txt

    if 'key="game_psy"' in txt:
        r["warns"].append("game.py: кнопка 🔮 уже есть")
        return

    # Найти кнопку "Бой"
    m = re.search(
        r'(\n)(\s*)if st\.button\([^\)]*key="game_combat"[^\)]*\):',
        txt,
    )
    if not m:
        r["warns"].append('game.py: не нашёл key="game_combat"')
        return

    indent = m.group(2)
    line_start = m.start() + 1

    psy_block = (
        indent + "# PATCH_87: кнопка Пси-силы\n"
        + indent + "try:\n"
        + indent + "    from services.psy_archetypes import ensure_psy_fields as _epf\n"
        + indent + "    _changed = _epf(char)\n"
        + indent + "    if _changed:\n"
        + indent + "        try:\n"
        + indent + "            from persistence.characters import save_character as _ssave\n"
        + indent + "            _ssave(login, char_name, char)\n"
        + indent + "        except Exception:\n"
        + indent + "            pass\n"
        + indent + "except Exception as _e:\n"
        + indent + "    print(\"[game] ensure_psy fail: \" + type(_e).__name__)\n"
        + indent + "try:\n"
        + indent + "    from services import psychic as _pmod\n"
        + indent + "    _p_blocked = _pmod.is_blocked(char)\n"
        + indent + "    _p_rating = int(char.get(\"psy_rating\", 0) or 0)\n"
        + indent + "except Exception:\n"
        + indent + "    _p_blocked = True\n"
        + indent + "    _p_rating = 0\n"
        + indent + "if _p_rating > 0 and not _p_blocked:\n"
        + indent + "    if st.button(\"\\U0001F52E \\u041f\\u0441\\u0438-\\u0441\\u0438\\u043b\\u044b\", use_container_width=True,\n"
        + indent + "                 key=\"game_psy\"):\n"
        + indent + "        st.session_state.screen = \"psy\"\n"
        + indent + "        st.rerun()\n"
    )
    txt = txt[:line_start] + psy_block + txt[line_start:]

    if txt != orig:
        if _write("ui/screens/game.py", txt):
            r["warns"].append("game.py: кнопка 🔮 вставлена")


_patch_game()


print("=== PATCH " + TAG + " ===")
for m in r["modified"]:
    print("  [MODIFIED] " + m)
for w in r["warns"]:
    print("  [INFO] " + w)
for e in r["errors"]:
    print("  [ERROR] " + e)
print("DONE" if not r["errors"] else "DONE (with errors)")