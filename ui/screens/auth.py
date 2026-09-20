# PATCH_11_COMPAT_V8

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
