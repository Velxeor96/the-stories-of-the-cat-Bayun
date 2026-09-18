"""Фикс: material icons + точечный ghost-kill вместо *."""
PATCH_MARKER = "41-icons-fix"
import ast, re, shutil
from pathlib import Path

print(f"[PATCH_MARKER] {PATCH_MARKER}")
ROOT = Path(__file__).resolve().parent.parent
RENDER = ROOT / "ui_render.py"
APP = ROOT / "app.py"

# ============================================================
# 0. ДИАГНОСТИКА: что в app.py с заголовками?
# ============================================================
print("\n=== ПРОВЕРКА ТЕКСТА В APP.PY ===")
asrc = APP.read_text(encoding="utf-8")
for needle in ["Что такое НРИ", "Что такое Warhammer", "Как играть"]:
    idx = asrc.find(needle)
    if idx > 0:
        chunk = asrc[idx:idx + len(needle) + 10]
        print(f"  [{needle!r}] найдено: {chunk!r}")
    else:
        print(f"  [{needle!r}] НЕ найдено")


# ============================================================
# 1. РЕКЛАССИФИКАЦИЯ ui_render.py
# ============================================================
print("\n=== ui_render.py ===")
rs = RENDER.read_text(encoding="utf-8")
try:
    ast.parse(rs)
except SyntaxError as e:
    raise SystemExit(f"[STOP] ui_render.py сломан: {e}")

# 1.1 УДАЛИТЬ СТАРЫЙ ГЛОБАЛЬНЫЙ БЛОК _GHOST_KILL_CSS
# Ищем по маркеру "# patch40: kill ghost (global)" до конца функции _inject_ghost_kill
old_block = re.search(
    r"# patch40: kill ghost \(global\).*?def _inject_ghost_kill\(\):\n[^\n]*\n",
    rs, re.DOTALL,
)
if old_block:
    rs = rs[:old_block.start()] + rs[old_block.end():]
    print("  старый ghost-kill удалён")
else:
    print("  [WARN] старый ghost-kill не найден")


# 1.2 НОВЫЙ БЛОК — ТОЧЕЧНЫЙ
NEW_BLOCK = '''

# patch41: kill ghost (targeted, без *)
_GHOST_KILL_CSS = """
<style>
/* ==========================================================
   MATERIAL SYMBOLS — ВОЗВРАЩАЕМ ИХ РОДНОЙ ШРИФТ.
   Streamlit рисует иконки expander лигатурами типа
   'keyboard_arrow_right'. Без родного шрифта они видны как
   обычный текст — отсюда «arrИво exactly».
   ========================================================== */
.material-symbols-rounded,
.material-symbols-outlined,
.material-symbols-sharp,
.material-icons,
.material-icons-outlined,
.material-icons-round,
[data-testid="stIconMaterial"],
[data-testid="stIconMaterial"] *,
span[class*="material-symbols"],
span[class*="material-icons"],
[class*="material-symbol"] {
    font-family: 'Material Symbols Rounded', 'Material Symbols Outlined',
                 'Material Icons', 'Material Icons Outlined' !important;
    font-feature-settings: 'liga' !important;
    -webkit-font-feature-settings: 'liga' !important;
    font-variant: normal !important;
    text-transform: none !important;
    letter-spacing: normal !important;
    line-height: 1 !important;
    transform: none !important;
    transition: none !important;
    font-size: inherit !important;
}

/* ==========================================================
   КНОПКИ — точечно
   ========================================================== */
.stButton > button,
.stButton > button *,
.stButton > button p,
.stButton > button span,
[data-testid="stBaseButton-primary"],
[data-testid="stBaseButton-primary"] *,
[data-testid="stBaseButton-secondary"],
[data-testid="stBaseButton-secondary"] * {
    text-transform: none !important;
    letter-spacing: 0 !important;
    transform: none !important;
    transition: none !important;
    animation: none !important;
    clip-path: none !important;
    -webkit-clip-path: none !important;
    white-space: normal !important;
    font-size: 1rem !important;
    line-height: 1.4 !important;
    font-variant: normal !important;
    font-feature-settings: normal !important;
}

/* ==========================================================
   EXPANDER — только summary-текст, БЕЗ svg
   ========================================================== */
[data-testid="stExpander"] summary,
[data-testid="stExpander"] summary p,
[data-testid="stExpander"] summary > div,
[data-testid="stExpander"] [data-testid="stExpanderHeader"],
[data-testid="stExpander"] [data-testid="stExpanderHeader"] p {
    text-transform: none !important;
    letter-spacing: 0 !important;
    transform: none !important;
    transition: none !important;
    animation: none !important;
    font-size: 1rem !important;
    line-height: 1.4 !important;
    font-variant: normal !important;
    font-feature-settings: normal !important;
    white-space: normal !important;
}

/* Скрыть возможные a11y-дубли в summary — но НЕ material icons */
[data-testid="stExpander"] summary .sr-only,
[data-testid="stExpander"] summary .visually-hidden {
    display: none !important;
    position: absolute !important;
    left: -9999px !important;
    width: 0 !important;
    height: 0 !important;
    overflow: hidden !important;
}
</style>
"""


def _inject_ghost_kill():
    st.markdown(_GHOST_KILL_CSS, unsafe_allow_html=True)
'''

rs = rs.rstrip() + NEW_BLOCK
print("  новый ghost-kill вставлен (точечный, без *)")

# 1.3 Убедиться, что _inject_ghost_kill вызывается ровно один раз
# Убрать все существующие вызовы, потом вставить один
rs = re.sub(r"^[ \t]*_inject_ghost_kill\(\)[ \t]*\n", "", rs, flags=re.MULTILINE)
anchor = "st.markdown(SIDEBAR_FIX_CSS, unsafe_allow_html=True)"
if anchor in rs:
    rs = rs.replace(anchor, anchor + "\n    _inject_ghost_kill()", 1)
    print("  _inject_ghost_kill подключено ровно 1 раз")
else:
    raise SystemExit("Не нашёл якорь SIDEBAR_FIX_CSS")


# 1.4 Не забыть: вернуть нормальный font-size для body, чтобы onboarding читался
# Здесь ничего не делаем — тема сама задаёт.

try:
    ast.parse(rs)
except SyntaxError as e:
    print(f"[FAIL] ui_render.py: {e}")
    raise SystemExit(1)

bak = RENDER.with_suffix(".py.bak41")
if not bak.exists():
    shutil.copy2(RENDER, bak)
    print(f"  [ok] бэкап: {bak.name}")
RENDER.write_text(rs, encoding="utf-8")
print(f"  [ok] ui_render.py записан ({len(rs)} символов)")


# ============================================================
# 2. Диагностика после
# ============================================================
print("\n=== ДИАГНОСТИКА ===")
r_final = RENDER.read_text(encoding="utf-8")
print(f"  '*' глобальный override  : {'*,' in r_final or '* {' in r_final}")
print(f"  material-symbols         : {r_final.count('material-symbols')}")
print(f"  text-transform: uppercase: {r_final.count('text-transform: uppercase')}")
print(f"  _inject_ghost_kill()     : {r_final.count('_inject_ghost_kill()')}")

print("\nOK, патч №41 применён.")
print("Запусти: python scripts\\dev.py check")
print("Потом:   ЗАКРОЙ Streamlit (Ctrl+C) и запусти python scripts\\dev.py run")