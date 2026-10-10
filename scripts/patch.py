# scripts/patch.py — PATCH_71: moderator refusal (безопасная вставка)
from __future__ import annotations
import ast, shutil, sys
from pathlib import Path

TAG = "PATCH_71"
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

p = ROOT / "services" / "moderator.py"
text = p.read_text(encoding="utf-8")

MARKER = "# PATCH_71: refusal detect (moderator)"

HELPER = '''
# PATCH_71: refusal detect (moderator)
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
# /PATCH_71

'''

# Безопасная точка вставки — непосредственно перед class ModeratorError
CLASS_ANCHOR = "class ModeratorError(Exception):"

OLD_RAISE = '            raise ModeratorError(f"JSON не найден: {text[:120]!r}")'
NEW_RAISE = '''            if _moderator_is_refusal(text):
                raise ModeratorError("GigaChat refused")
            raise ModeratorError(f"JSON не найден: {text[:120]!r}")'''

if MARKER in text:
    r["modified"].append("moderator.py — уже пропатчен")
elif CLASS_ANCHOR not in text:
    r["errors"].append("moderator.py: class ModeratorError не найден")
elif OLD_RAISE not in text:
    r["errors"].append("moderator.py: raise ModeratorError не найден")
else:
    # 1) helper ПЕРЕД классом — там точно можно (после всех импортов)
    text = text.replace(CLASS_ANCHOR, HELPER + CLASS_ANCHOR, 1)
    # 2) raise c проверкой
    text = text.replace(OLD_RAISE, NEW_RAISE, 1)
    try:
        ast.parse(text)
    except SyntaxError as e:
        r["errors"].append("moderator.py syntax: " + str(e) + " (line " + str(e.lineno) + ")")
    else:
        _bk(p)
        p.write_text(text, encoding="utf-8")
        r["modified"].append("moderator.py — +refusal detect")

print("=== PATCH " + TAG + " ===")
for m in r["modified"]:
    print("  [MODIFIED] " + m)
for e in r["errors"]:
    print("  [ERROR] " + e)
print("DONE" if not r["errors"] else "DONE (with errors)")