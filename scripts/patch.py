"""scripts/patch.py — патч #11 V8: fix login loop."""
from __future__ import annotations

import ast
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TAG = "PATCH_11_COMPAT_V8"


AUTH_NEW = r"""
'''ui/screens/auth.py — вход и регистрация (V8).'''
from __future__ import annotations

import streamlit as st

import persistence.accounts as _acc
from ui.assets import sigil_svg
from ui.theme import _current


def _find(*names):
    for n in names:
        if hasattr(_acc, n):
            return getattr(_acc, n)
    return None


_LOGIN = _find("verify_user", "authenticate", "login",
               "login_user", "verify_login", "check_credentials")
_CREATE = _find("register_user", "create_account", "register",
                "create_user", "new_account")
_ERR = _find("AuthError", "AccountError", "AccountsError") or Exception


AUTH_CSS = '''
<style>
.auth-wrap { max-width: 480px; margin: 40px auto 20px auto;
             padding: 0 16px; animation: fadeInUp 0.7s ease-out; }
.auth-hero { text-align: center; margin-bottom: 20px; }
.auth-hero h1 {
    font-family: Georgia, serif; font-size: 32px; color: var(--fg);
    letter-spacing: 3px; margin: 14px 0 0 0;
    text-shadow: 0 0 20px var(--accent-glow);
}
.auth-hero .sub {
    color: var(--fg-dim); font-style: italic;
    font-size: 13px; margin-top: 6px; letter-spacing: 1px;
}
.auth-divider {
    text-align: center; color: var(--accent);
    letter-spacing: 10px; font-size: 12px;
    margin: 10px 0 10px 0; opacity: 0.55;
}
[data-testid="stTextInput"] input {
    background: var(--panel) !important;
    color: var(--fg) !important;
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
    padding: 10px 12px !important;
    font-size: 15px !important;
}
[data-testid="stTextInput"] input:focus {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 2px var(--accent-glow) !important;
    outline: none !important;
}
[data-testid="stTextInput"] input::placeholder {
    color: var(--fg-dim) !important;
    opacity: 0.45 !important;
    font-style: italic;
}
[data-testid="stTextInput"] label {
    color: var(--fg-dim) !important;
    font-size: 12px !important;
    letter-spacing: 1px !important;
    text-transform: uppercase !important;
}
input[aria-label="Пароль"],
input[aria-label="Повтори пароль"],
input[placeholder=" "] {
    -webkit-text-security: disc !important;
    font-family: 'Consolas', monospace !important;
    letter-spacing: 2px !important;
}
[data-baseweb="tab-list"] {
    gap: 8px !important;
    border-bottom: 1px solid var(--border) !important;
}
[data-baseweb="tab"] {
    background: transparent !important;
    color: var(--fg-dim) !important;
    font-family: Georgia, serif !important;
    letter-spacing: 1px !important;
    padding: 10px 16px !important;
}
[aria-selected="true"][data-baseweb="tab"] {
    color: var(--accent) !important;
    border-bottom: 2px solid var(--accent) !important;
}
</style>
'''


def _safe_call(fn, *args):
    try:
        return True, fn(*args)
    except _ERR as e:
        return False, str(e)
    except TypeError as e:
        try:
            if len(args) == 2:
                return True, fn(login=args[0], password=args[1])
        except Exception as e2:
            return False, str(e) + " / " + str(e2)
        return False, str(e)
    except Exception as e:
        return False, type(e).__name__ + ": " + str(e)


def _after_login(name):
    '''Общий код после успешного логина.'''
    st.session_state.user_login = name
    st.session_state.pop("orchestrator", None)
    st.session_state.pop("active_character", None)
    # НЕ ставим splash — app.py сам выберет следующий экран
    st.session_state.screen = "wizard"
    st.rerun()


def _do_login(name, password):
    name = (name or "").strip()
    password = password or ""
    if not name or not password:
        st.error("Заполни оба поля: логин и пароль.")
        return
    if _LOGIN is None:
        st.error("В persistence/accounts.py нет verify_user.")
        return
    ok, result = _safe_call(_LOGIN, name, password)
    if not ok:
        st.error(str(result))
        return
    if result is False or result is None:
        st.error("Неверный логин или пароль.")
        return
    _after_login(name)


def _do_register(name, password, password2):
    name = (name or "").strip()
    password = password or ""
    password2 = password2 or ""
    if not name or not password:
        st.error("Заполни логин и пароль.")
        return
    if password != password2:
        st.error("Пароли не совпадают.")
        return
    if len(password) < 4:
        st.error("Пароль слишком короткий (минимум 4).")
        return
    if _CREATE is None:
        st.error("В persistence/accounts.py нет register_user.")
        return
    ok, result = _safe_call(_CREATE, name, password)
    if not ok:
        st.error(str(result))
        return
    _after_login(name)


def render():
    st.markdown(AUTH_CSS, unsafe_allow_html=True)
    theme = _current()
    sigil = sigil_svg(theme, size=72)

    st.markdown(
        "<div class='auth-wrap'><div class='auth-hero'>" + sigil +
        "<h1>ВОЙТИ</h1>"
        "<div class='sub'>Потент ждёт подписи</div>"
        "</div></div>",
        unsafe_allow_html=True,
    )

    tab_login, tab_reg = st.tabs(["Вход", "Регистрация"])

    with tab_login:
        login_name = st.text_input("Логин", key="auth_login_name")
        password = st.text_input("Пароль", key="auth_login_pwd",
                                 placeholder=" ")
        st.markdown("<div class='auth-divider'>❦ ❦ ❦</div>",
                    unsafe_allow_html=True)
        if st.button("▶  Войти", use_container_width=True,
                     type="primary", key="btn_do_login"):
            _do_login(login_name, password)

    with tab_reg:
        login_name = st.text_input("Логин", key="auth_reg_name")
        password = st.text_input("Пароль", key="auth_reg_pwd",
                                 placeholder=" ")
        password2 = st.text_input("Повтори пароль", key="auth_reg_pwd2",
                                  placeholder=" ")
        st.markdown("<div class='auth-divider'>❦ ❦ ❦</div>",
                    unsafe_allow_html=True)
        if st.button("✎  Создать аккаунт", use_container_width=True,
                     type="primary", key="btn_do_register"):
            _do_register(login_name, password, password2)

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("←  На главную", key="auth_back"):
        st.session_state.screen = "splash"
        st.rerun()
"""


APP_NEW = r"""
'''app.py — точка входа и маршрутизация (V8).'''
import streamlit as st

st.set_page_config(
    page_title="Warhammer 40K RPG",
    page_icon="⚔️",
    layout="wide",
)

if "screen" not in st.session_state:
    st.session_state.screen = "splash"

from ui.screens import (  # noqa: E402
    splash, about, auth, onboarding, tutorial, wizard, game,
    kot_intro, tutorial_prompt, tutorial_help,
)
from ui.theme import apply_theme  # noqa: E402

apply_theme()

SCREENS = {
    "splash": splash.render,
    "about": about.render,
    "auth": auth.render,
    "onboarding": onboarding.render,
    "kot_intro": kot_intro.render,
    "tutorial_prompt": tutorial_prompt.render,
    "tutorial_help": tutorial_help.render,
    "tutorial": tutorial.render,
    "wizard": wizard.render,
    "game": game.render,
}


def _setting(login, key, default=False):
    try:
        from persistence.settings import get_setting
        return bool(get_setting(login, key, default))
    except Exception:
        return default


def _has_any_character(login):
    try:
        from persistence.characters import has_any
        return bool(has_any(login))
    except Exception:
        return False


def _resolve_screen():
    '''Главный роутер. Решает, какой экран показать прямо сейчас.'''
    screen = st.session_state.get("screen", "splash")
    login = st.session_state.get("user_login")

    # --- НЕ залогинен ---
    if not login:
        if screen not in ("splash", "auth", "about"):
            return "splash"
        return screen

    # --- Залогинен ---
    # Онбординг (необязательный) — если ещё не видел, показать 1 раз
    if screen == "onboarding":
        if not _setting(login, "seen_onboarding"):
            return "onboarding"
        st.session_state.screen = "wizard"
        screen = "wizard"

    # Если сидит на login-экранах после успешного логина — гоним дальше
    if screen in ("splash", "auth", "about"):
        screen = "wizard"

    # Первый раз: Кот Баюн
    if not _setting(login, "kot_intro_seen"):
        return "kot_intro"

    # Второй раз: предложение обучения
    if not _setting(login, "seen_tutorial"):
        return "tutorial_prompt"

    # Всё видел — решаем по наличию персонажа
    if screen in ("wizard", "game"):
        if not _has_any_character(login):
            return "wizard"
        return "game"

    # Пропускаем как есть
    if screen in SCREENS:
        return screen

    # Фолбэк
    return "wizard"


screen = _resolve_screen()
if screen in SCREENS:
    SCREENS[screen]()
else:
    st.warning(f"Неизвестный экран: {screen!r}")
    if st.button("← На главную"):
        st.session_state.screen = "splash"
        st.rerun()
"""


# =====================================================================
# SAFE
# =====================================================================
def _safe(content, name):
    try:
        ast.parse(content)
        return True
    except SyntaxError as e:
        print("[INTERNAL ERROR] " + name + ": " + str(e))
        print("Line " + str(e.lineno) + ": " + (e.text or "").rstrip())
        return False


def _backup(path):
    bak = path.with_name(path.name + ".bak_pre_" + TAG)
    if bak.exists():
        return
    shutil.copy2(path, bak)
    print("[backup] " + bak.name)


def _write(rel, content):
    path = ROOT / rel
    if path.exists():
        old = path.read_text(encoding="utf-8")
        if TAG in old:
            print("[skip]   " + rel + " — уже пропатчен")
            return False
        _backup(path)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("# " + TAG + "\n" + content, encoding="utf-8")
    try:
        ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError as e:
        print("[ERROR]  " + rel + " после записи: " + str(e))
        return False
    print("[patch]  " + rel + " — ok")
    return True


def main():
    print("=== Patch " + TAG + " ===")

    if not _safe(AUTH_NEW, "AUTH_NEW"):
        return 1
    if not _safe(APP_NEW, "APP_NEW"):
        return 1
    print("[preflight] оба блока парсятся — ок")
    print()

    _write("ui/screens/auth.py", AUTH_NEW)
    _write("app.py", APP_NEW)

    print()
    print("Перезапусти:")
    print("  Ctrl+C → streamlit run app.py → F5")
    print()
    print("Ожидаемый флоу:")
    print("  splash → auth → [вход] → Кот Баюн →")
    print("  'Желаешь обучение?' → ДА/НЕТ/НЕ ЗНАЮ → ...")
    return 0


if __name__ == "__main__":
    sys.exit(main())