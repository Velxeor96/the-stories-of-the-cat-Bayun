# scripts/patch.py — PATCH_70: точные якоря refusal для analyst + moderator
from __future__ import annotations
import ast, shutil, sys
from pathlib import Path

TAG = "PATCH_70"
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
# 1) services/analyst.py
# ============================================================
p = ROOT / "services" / "analyst.py"
text = p.read_text(encoding="utf-8")

MARKER_A = "# PATCH_70: refusal detect (analyst)"

HELPER_A = '''# PATCH_70: refusal detect (analyst)
def _analyst_is_refusal(text: str) -> bool:
    """True, если GigaChat вернул отписку вместо JSON."""
    if not text:
        return False
    low = str(text).lower()
    for m in (
        "не обладает собственным мнением",
        "не транслирует мнение",
        "как и любая языковая модель",
        "иногда генеративные языковые модели",
        "generative language model",
        "обобщением информации",
    ):
        if m.lower() in low:
            return True
    return False
# /PATCH_70

'''

# Точный якорь из дампа
OLD_RAISE = '''        m = _JSON_RE.search(text)
        if not m:
            raise AnalystError("не найден JSON: " + repr(text[:120]))'''

NEW_RAISE = '''        m = _JSON_RE.search(text)
        if not m:
            if _analyst_is_refusal(text):
                raise AnalystError("GigaChat refused")
            raise AnalystError("не найден JSON: " + repr(text[:120]))'''

if MARKER_A in text:
    r["modified"].append("analyst.py — уже пропатчен")
elif OLD_RAISE in text:
    # Вставляем helper в начало, после импортов
    # Найдём первую пустую строку после __future__ import
    insert_after = text.find("\n\n")
    if insert_after > 0:
        # Сдвигаемся на два \n вперёд
        insert_after += 2
        text = text[:insert_after] + HELPER_A + text[insert_after:]
    else:
        text = HELPER_A + text
    # Заменяем raise
    text = text.replace(OLD_RAISE, NEW_RAISE, 1)
    try:
        ast.parse(text)
    except SyntaxError as e:
        r["errors"].append("analyst.py syntax: " + str(e))
    else:
        _bk(p)
        p.write_text(text, encoding="utf-8")
        r["modified"].append("analyst.py — +refusal detect")
else:
    r["errors"].append("analyst.py: якорь '_JSON_RE.search(text)' не найден")

# ============================================================
# 2) services/moderator.py
# ============================================================
p = ROOT / "services" / "moderator.py"
text = p.read_text(encoding="utf-8")

MARKER_M = "# PATCH_70: refusal detect (moderator)"

HELPER_M = '''# PATCH_70: refusal detect (moderator)
def _moderator_is_refusal(text: str) -> bool:
    """True, если GigaChat вернул отписку вместо JSON."""
    if not text:
        return False
    low = str(text).lower()
    for m in (
        "не обладает собственным мнением",
        "не транслирует мнение",
        "как и любая языковая модель",
        "иногда генеративные языковые модели",
        "generative language model",
        "обобщением информации",
    ):
        if m.lower() in low:
            return True
    return False
# /PATCH_70

'''

# Точный якорь из дампа — f-string!
OLD_RAISE_M = '            raise ModeratorError(f"JSON не найден: {text[:120]!r}")'

NEW_RAISE_M = '''            if _moderator_is_refusal(text):
                raise ModeratorError("GigaChat refused")
            raise ModeratorError(f"JSON не найден: {text[:120]!r}")'''

if MARKER_M in text:
    r["modified"].append("moderator.py — уже пропатчен")
elif OLD_RAISE_M in text:
    insert_after = text.find("\n\n")
    if insert_after > 0:
        insert_after += 2
        text = text[:insert_after] + HELPER_M + text[insert_after:]
    else:
        text = HELPER_M + text
    text = text.replace(OLD_RAISE_M, NEW_RAISE_M, 1)
    try:
        ast.parse(text)
    except SyntaxError as e:
        r["errors"].append("moderator.py syntax: " + str(e))
    else:
        _bk(p)
        p.write_text(text, encoding="utf-8")
        r["modified"].append("moderator.py — +refusal detect")
else:
    r["errors"].append("moderator.py: якорь 'JSON не найден' не найден")

print("=== PATCH " + TAG + " ===")
for m in r["modified"]:
    print("  [MODIFIED] " + m)
for e in r["errors"]:
    print("  [ERROR] " + e)
print("DONE" if not r["errors"] else "DONE (with errors)")