# scripts/patch.py
# PATCH_16K — разделяем «Главное меню» и «Выход».
# Запуск: python scripts\patch.py
from __future__ import annotations

import ast
import shutil
import sys
from pathlib import Path

TAG = "PATCH_16K"
ROOT = Path(__file__).resolve().parent.parent


def _read_game():
    p = ROOT / "ui" / "screens" / "game.py"
    if not p.exists():
        return None, "ERROR: game.py not found"
    try:
        return p, p.read_text(encoding="utf-8")
    except Exception as e:
        return None, "ERROR read: " + type(e).__name__ + ": " + str(e)


def _write_game(p, src):
    try:
        ast.parse(src)
    except SyntaxError as e:
        return "ERROR SyntaxError: line " + str(e.lineno) + ": " + str(e.msg)
    bak = p.with_name(p.name + ".bak_pre_" + TAG)
    try:
        shutil.copy2(p, bak)
    except Exception as e:
        return "ERROR backup: " + type(e).__name__ + ": " + str(e)
    try:
        p.write_text(src, encoding="utf-8")
    except Exception as e:
        return "ERROR write: " + type(e).__name__ + ": " + str(e)
    return "backup + patched"


# =====================================================================
# 1. Заменить _logout на пару: _back_to_menu + новый _logout
# =====================================================================
def step_logout_split():
    p, src = _read_game()
    if p is None:
        return src

    old = (
        "def _logout() -> None:\n"
        "    for k in (\"user_login\", \"active_character\", \"orchestrator\",\n"
        "              \"tutorial_mode\", \"roll_card_variant\"):\n"
        "        st.session_state.pop(k, None)\n"
        "    st.session_state.screen = \"main_menu\"\n"
        "    st.rerun()\n"
    )
    new = (
        "def _back_to_menu() -> None:\n"
        "    # Возврат в главное меню: login сохраняем, чистим только сессию игры.\n"
        "    for k in (\"active_character\", \"_game_loading_pending\",\n"
        "              \"_game_loading_ready\", \"_roll_dialog_state\",\n"
        "              \"_attack_open\", \"_attack_weapon\", \"_attack_result\",\n"
        "              \"_pending_chat\"):\n"
        "        st.session_state.pop(k, None)\n"
        "    st.session_state.screen = \"main_menu\"\n"
        "    st.rerun()\n"
        "\n"
        "\n"
        "def _logout() -> None:\n"
        "    # Полный выход: удаляем логин, сбрасываем landing-флаг.\n"
        "    for k in (\"user_login\", \"active_character\", \"orchestrator\",\n"
        "              \"tutorial_mode\", \"roll_card_variant\",\n"
        "              \"_post_login_landed_for\", \"_game_loading_pending\",\n"
        "              \"_game_loading_ready\", \"_roll_dialog_state\",\n"
        "              \"_attack_open\", \"_attack_weapon\", \"_attack_result\",\n"
        "              \"_pending_chat\"):\n"
        "        st.session_state.pop(k, None)\n"
        "    st.session_state.screen = \"splash\"\n"
        "    st.rerun()\n"
    )

    if old not in src:
        if "def _back_to_menu()" in src:
            return "skip (already patched)"
        return "ERROR: _logout anchor not found"
    src2 = src.replace(old, new, 1)
    return _write_game(p, src2)


# =====================================================================
# 2. Заменить одну кнопку на две в сайдбаре
# =====================================================================
def step_sidebar_buttons():
    p, src = _read_game()
    if p is None:
        return src

    old = (
        '        if st.button("Выйти в меню", use_container_width=True, key="game_exit"):\n'
        '            _logout()\n'
    )
    new = (
        '        if st.button("Главное меню", use_container_width=True,\n'
        '                     key="game_to_menu"):\n'
        '            _back_to_menu()\n'
        '        if st.button("Выход", use_container_width=True, key="game_exit"):\n'
        '            _logout()\n'
    )

    if old not in src:
        if 'key="game_to_menu"' in src:
            return "skip (already patched)"
        return "ERROR: sidebar buttons anchor not found"
    src2 = src.replace(old, new, 1)
    return _write_game(p, src2)


# =====================================================================
# 3. Проверка
# =====================================================================
def final_check():
    p, src = _read_game()
    if p is None:
        return False, "game.py not found"
    try:
        ast.parse(src)
    except SyntaxError as e:
        return False, "line " + str(e.lineno) + ": " + str(e.msg)

    if "def _back_to_menu()" not in src:
        return False, "_back_to_menu missing"
    if 'st.session_state.screen = "splash"' not in src:
        return False, "_logout doesn't go to splash"
    if 'key="game_to_menu"' not in src:
        return False, "menu button missing"
    return True, "OK"


def main():
    print("=" * 64)
    print("PATCH " + TAG + " — Главное меню vs Выход")
    print("ROOT: " + str(ROOT))
    print("=" * 64)

    any_error = False

    print("[1/3] Разделить _logout на _back_to_menu + _logout:")
    status = step_logout_split()
    if status.startswith("ERROR"):
        any_error = True
    print("      -> " + status)

    print("[2/3] Заменить кнопку в сайдбаре:")
    status = step_sidebar_buttons()
    if status.startswith("ERROR"):
        any_error = True
    print("      -> " + status)

    print("[3/3] Финальная проверка:")
    ok, msg = final_check()
    print("      -> " + msg)
    if not ok:
        any_error = True

    print("=" * 64)
    print("DONE" + (" (with errors)" if any_error else " — ok"))
    return 1 if any_error else 0


if __name__ == "__main__":
    sys.exit(main())