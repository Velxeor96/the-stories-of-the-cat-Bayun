# scripts/patch.py — PATCH_68: continuation prompt + choice hint + diagnostics
from __future__ import annotations
import ast, re, shutil, sys
from pathlib import Path

TAG = "PATCH_68"
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
# 1) prompts/master_core.txt — секция «ПРОДОЛЖЕНИЕ ИСТОРИИ»
# ============================================================
p = ROOT / "prompts" / "master_core.txt"
text = p.read_text(encoding="utf-8")

MARKER = "ПРОДОЛЖЕНИЕ ИСТОРИИ"

CONTINUATION = """---

## 📖 ПРОДОЛЖЕНИЕ ИСТОРИИ

В блоке **«ПОСЛЕДНИЕ ХОДЫ»** (если он есть) ты видишь прошлые реплики игрока
и свои собственные ответы. Это твоя память о разговоре.

### Жёсткие правила

- **НЕ НАЧИНАЙ СЦЕНУ ЗАНОВО.** Если ты уже описал «Ты стоишь на мосту…» —
  второй раз так не пиши. Продолжай с того момента, где остановился.
- **ПОМНИ NPC, места, договорённости.** Если раньше был инквизитор Драган —
  это он и в следующем ходу. Если игрок обещал встретиться — он помнит.
- **ЕСЛИ ИГРОК ПИШЕТ «1», «2», «3», «4»** — это номер из твоего последнего
  блока «Варианты действий». Ты **обязан** описать, что происходит, когда
  игрок делает этот выбор. Не спрашивай «что делаешь?» снова — просто
  опиши последствия.
- **ЕСЛИ ИГРОК ПИШЕТ СВОБОДНО** («Я иду к башне») — это действие, продолжай
  сцену от текущего момента, не от начала.

### Как понять, что ты повторяешься

Признаки «начала заново»:
- Ты описываешь первую сцену (место, где игрок «только что прибыл»).
- Ты говоришь «Ты стоишь на…» в третий раз.
- Ты описываешь NPC, который уже был представлен.
- Ты повторяешь атмосферные детали (погоду, запахи) без причины.

Если такое ловишь — **остановись** и продолжай с того места, где закончился
предыдущий ответ. Продвинь сюжет вперёд хотя бы на одну деталь:
новый NPC, новая угроза, новая зацепка, поворот.

### Формат ответа (напоминание)

1. Художественное описание (3-5 абзацев) — **продолжение**, не заново.
2. Короткий вопрос в конце.
3. **Варианты действий:** 2-4 варианта + «Иное: опиши».

"""

if MARKER in text:
    r["modified"].append("master_core.txt — секция ПРОДОЛЖЕНИЕ ИСТОРИИ уже есть")
else:
    m = re.search(r'\n##\s+[^\n]*ТОН\s+И\s+СТИЛЬ[^\n]*\n', text)
    if m:
        pos = m.start()
        nt = text[:pos] + "\n" + CONTINUATION + text[pos+1:]
        _bk(p)
        p.write_text(nt, encoding="utf-8")
        r["modified"].append("master_core.txt — +ПРОДОЛЖЕНИЕ ИСТОРИИ")
    else:
        r["errors"].append("master_core.txt: якорь '## …ТОН И СТИЛЬ' не найден")

# ============================================================
# 2) services/orchestrator.py — подсказка при выборе цифры
# ============================================================
p = ROOT / "services" / "orchestrator.py"
text = p.read_text(encoding="utf-8")

MARKER_ORCH = "# PATCH_68: continuation + choice hint"

if MARKER_ORCH in text:
    r["modified"].append("orchestrator.py — уже пропатчен")
else:
    # 2а) добавить функцию _parse_master_choices после DEFAULT_SKILL_VALUE
    ANCHOR_TOP = "DEFAULT_SKILL_VALUE = 45\n"
    HELPER = '''

# PATCH_68: continuation + choice hint
def _parse_master_choices(text: str) -> list[str]:
    """Извлекает список вариантов действий из последнего ответа мастера."""
    if not text:
        return []
    import re as _re
    m = _re.search(
        r"(?i)(?:\\*\\*)?(варианты\\s+действий|варианты)(?:\\*\\*)?[^\\n]*\\n((?:.|\\n)*)",
        text,
    )
    if not m:
        return []
    block = m.group(2)
    entries: dict = {}
    for line in block.split("\\n"):
        mm = _re.match(
            r"^\\s*(\\d+)\\.\\s+\\*\\*(.+?)\\*\\*[.\\s]*(.*)$",
            line.strip(),
        )
        if mm:
            n = int(mm.group(1))
            title = mm.group(2).strip()
            body = mm.group(3).strip()
            entries[n] = title + (". " + body if body else "")
    return [entries[k] for k in sorted(entries.keys())]


def _choice_hint_for(player_input: str, history: list) -> str:
    """Если ввод — номер 1..9, возвращает подсказку мастеру с текстом выбора."""
    s = str(player_input).strip()
    if s not in ("1", "2", "3", "4", "5", "6", "7", "8", "9"):
        return ""
    if not history:
        return ""
    n = int(s)
    last_master = ""
    for t in reversed(history):
        if isinstance(t, dict) and str(t.get("role")) == "master":
            last_master = str(t.get("text", ""))
            break
    if not last_master:
        return ""
    choices = _parse_master_choices(last_master)
    if not choices or n > len(choices):
        return ""
    return (
        "\\n\\n=== ВЫБОР ИГРОКА ===\\n"
        "Игрок написал \\"" + s + "\\" — это означает, что он выбирает "
        "вариант " + str(n) + " из твоего последнего блока «Варианты действий»:\\n"
        "«" + choices[n-1] + "»\\n"
        "Опиши, что происходит, когда игрок делает этот выбор. "
        "НЕ повторяй вступление и НЕ задавай вопрос «что делаешь?» снова — "
        "сразу переходи к последствиям и новой сцене."
    )
# /PATCH_68

'''

    # 2б) заменить extra_context=rag_ctx на extra_context=(rag_ctx or "") + _choice_hint
    OLD_CALL = '''        narrative = self.master.narrate(
            state, command, roll=roll, history=history or [],
            extra_context=rag_ctx,
        )'''
    NEW_CALL = '''        # PATCH_68: подсказка мастеру, если игрок выбрал вариант цифрой
        _choice_hint = _choice_hint_for(player_input, history or [])
        if _choice_hint:
            print("[orchestrator] choice hint: " + player_input.strip())
        narrative = self.master.narrate(
            state, command, roll=roll, history=history or [],
            extra_context=(rag_ctx or "") + _choice_hint,
        )'''

    changed = 0
    if ANCHOR_TOP in text:
        text = text.replace(ANCHOR_TOP, ANCHOR_TOP + HELPER, 1)
        changed += 1
    else:
        r["errors"].append("orchestrator.py: якорь DEFAULT_SKILL_VALUE не найден")

    if OLD_CALL in text:
        text = text.replace(OLD_CALL, NEW_CALL, 1)
        changed += 1
    else:
        r["errors"].append("orchestrator.py: блок narrate(...) не найден")

    if changed == 2:
        try:
            ast.parse(text)
        except SyntaxError as e:
            r["errors"].append("orchestrator.py syntax: " + str(e))
        else:
            _bk(p)
            p.write_text(text, encoding="utf-8")
            r["modified"].append("orchestrator.py — +_choice_hint + _parse_master_choices")

# ============================================================
# 3) Диагностика analyst.py и moderator.py (для PATCH_69)
# ============================================================
for rel, out_name in [
    ("services/analyst.py",   "_d68_analyst.txt"),
    ("services/moderator.py", "_d68_moderator.txt"),
]:
    fp = ROOT / rel
    if not fp.exists():
        continue
    lines = fp.read_text(encoding="utf-8", errors="ignore").split("\n")
    body = [f"=== {rel}: {len(lines)} строк ===", ""]
    for i, ln in enumerate(lines, 1):
        body.append(f"{i:5d} | {ln}")
    (ROOT / "scripts" / out_name).write_text("\n".join(body), encoding="utf-8")

print("=== PATCH " + TAG + " ===")
for m in r["modified"]:
    print("  [MODIFIED] " + m)
for e in r["errors"]:
    print("  [ERROR] " + e)
print("DONE" if not r["errors"] else "DONE (with errors)")
print("Дампы: scripts/_d68_analyst.txt, scripts/_d68_moderator.txt")