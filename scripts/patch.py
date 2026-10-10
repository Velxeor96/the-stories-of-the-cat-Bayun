# scripts/patch.py — PATCH_77: VERSION 1.8.0 + CHANGELOG + Gist retry
from __future__ import annotations
import ast, re, shutil, sys
from pathlib import Path

TAG = "PATCH_77"
NEW_VERSION = "1.8.0"
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

def _read_any(p: Path) -> str:
    for enc in ("utf-8", "cp1251", "latin-1"):
        try:
            return p.read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
    return p.read_text(encoding="utf-8", errors="replace")


# ============================================================
# 1) VERSION → 1.8.0
# ============================================================
p = ROOT / "VERSION"
old_version = _read_any(p).strip() if p.exists() else "?"
_bk(p)
p.write_text(NEW_VERSION + "\n", encoding="utf-8")
r["modified"].append(f"VERSION — {old_version} → {NEW_VERSION}")


# ============================================================
# 2) CHANGELOG.md — новая секция [1.8.0]
# ============================================================
CHANGELOG_SECTION = f"""## [{NEW_VERSION}] — 2026-10-10

Массивное обновление: пять новых субфракций Империума, облачные сохранения,
умный мастер с критическими исходами и полноценная работа в облаке.

### 🆕 Фракции и архетипы

- **Имперская Гвардия** — 12 архетипов (Водитель, Военный врач, Сержант,
  Тяжёлый стрелок, Стрелок, Комиссар, Огрин, Ратлинг, Псайкер, Священник,
  Техножрец, Штурмовик), 40 талантов, 8 родных миров, механика полков
  (командиры, типы, доктрины, недостатки), 9 известных полков, 3 именных NPC.
- **Адептус Механикус** — 5 архетипов (Техножрец, Магос, Эксплоратор,
  Генетор, Скитарий), 5 талантов.
- **Инквизиция** — 5 архетипов (Инквизитор, Аколит, Штурмовик, Псайкер,
  Крусейдер), 5 талантов.
- **Адепта Сороритас** — 5 архетипов (Сестра Битвы, Серафима, Доминион,
  Ритрибьютор, Целестина), 5 талантов.
- **Адептус Астартес** — 6 архетипов (Тактик, Девастатор, Ассаулт, Скаут,
  Библиарий, Апотекарий), 5 талантов.
- **Адептус Арбитрес** — 4 архетипа (Патрульный, Судья, Прокурор, Маршал),
  5 талантов.
- **Стартовые наборы субфракций** — уникальное оружие, броня и снаряжение
  для каждой субфракции (лазган + нож для ИГ, омниссианский топор для
  Механикус, болтер Астартес для Космодесанта и т.д.).
- **Бонусы архетипов** — характеристики теперь получают бонусы от выбранного
  архетипа (Магос +10 Int, Тактик Астартес +10 WS/BS/S/T и т.д.).

### 🎲 Мастер и правила

- **Блок `[STATE]`** — мастер возвращает изменения в конце ответа (опыт,
  деньги, раны, инвентарь, локация, NPC, квесты, эффекты, репутация, флаги
  сюжета, корабль).
- **Критические исходы** — крит. успех даёт сюжетный подарок, крит. провал —
  катастрофу; мастер обязан описывать последствия, а не просто «получилось/
  не получилось».
- **Деньги** — правила ценообразования (обычный предмет 5-50, хороший 100-500,
  редкий 1000-10000 тронов); clamp на 0 при отрицательном балансе.
- **Выбор вариантов** — игрок может ввести «1», «2», «3» вместо текста
  действия; система передаёт мастеру точный текст выбранного варианта.
- **Продолжение истории** — мастер больше не повторяет вступление, а
  продолжает сцену.
- **Обработка отказов GigaChat** — если модель отказывается отвечать,
  fallback-текст в роли мастера (без ошибок).

### ☁️ Облако

- **GitHub Gist для сохранений** — персонажи, чаты, настройки и аккаунты
  сохраняются в облако, переживают перезапуск Streamlit Cloud.
- **Авто-распаковка `chroma_db.zip`** — RAG-база работает в облаке без
  ручной распаковки.
- **HuggingFace offline** — модель эмбеддингов не пытается скачаться
  из интернета (важно для облака).
- **HF-модель в репо** — `intfloat/multilingual-e5-small` разбита на 4
  части по 70 МБ, распаковывается при старте.
- **Локальный fallback** — если облако недоступно, всё работает локально.

### 🎨 UI / UX

- **Локализация навыков и талантов** — английские `Tech-Use`, `Awareness`,
  `Forbidden Lore (Xenos)` и др. заменены на русские.
- **Кнопка «Корабль»** — видна только если у персонажа есть корабль
  (`has_ship`); у Вольного Торговца — по умолчанию.
- **Исправлено главное меню** — экраны «Загрузки», «Настройки», «Создатели»
  открываются корректно.
- **Тестеры** — обновлён список благодарностей: Ксения, Кайса, Puslik,
  Игорь, Сергей, Роман, Валерий, друзья Романа.

### 🔧 Инфраструктура

- **`.gitignore` в UTF-8** — исправлена кодировка комментариев.
- **Паттерны дампов** — `scripts/_d*.txt` и `scripts/_diag*.txt` не попадают
  в git автоматически.
- **Retry для Gist** — сохранения повторяются при сетевых сбоях (3 попытки
  с backoff).
- **Чистые бэкапы** — каждое изменение `.py` бэкапится перед патчем
  (`*.bak_pre_PATCH_*`).

### 🐛 Исправления

- **История ходов** — мастер корректно получает предыдущие ходы (dict vs
  TurnResult mismatch).
- **Импорт `_analyst_is_refusal`** — модуль модератора работал без errors.
- **Экраны `loads` / `settings_screen` / `credits`** — вернулись к своим
  рендерам (были заглушены game_settings).

---

"""

p = ROOT / "CHANGELOG.md"
old = _read_any(p)

# Проверка: если 1.8.0 уже есть — пропускаем
if f"[{NEW_VERSION}]" in old:
    r["modified"].append(f"CHANGELOG.md — [{NEW_VERSION}] уже есть")
else:
    _bk(p)
    # Если файл начинается с # — сохраняем заголовок
    if old.startswith("#"):
        first_nl = old.find("\n")
        if first_nl > 0:
            header = old[:first_nl]
            rest = old[first_nl + 1:].lstrip("\n")
            new_text = header + "\n\n" + CHANGELOG_SECTION + rest
        else:
            new_text = CHANGELOG_SECTION
    else:
        new_text = CHANGELOG_SECTION + old

    p.write_text(new_text, encoding="utf-8")
    r["modified"].append(f"CHANGELOG.md — +секция [{NEW_VERSION}]")


# ============================================================
# 3) cloud_store.py — retry с backoff
# ============================================================
p = ROOT / "persistence" / "cloud_store.py"
text = _read_any(p)

MARKER = "# PATCH_77: retry"

if MARKER in text:
    r["modified"].append("cloud_store.py — retry уже есть")
else:
    OLD_SAVE = '''def _save_gist(data: dict) -> bool:
    try:
        payload = {
            "files": {
                "wh40k_saves.json": {
                    "content": json.dumps(data, ensure_ascii=False, indent=2),
                }
            }
        }
        r = requests.patch(
            "https://api.github.com/gists/" + _GIST_ID,
            headers=_headers(),
            json=payload,
            timeout=15,
        )
        if r.status_code not in (200, 201):
            print("[cloud_store] PATCH fail: HTTP " + str(r.status_code)
                  + " " + r.text[:200])
            return False
        _CACHE["data"] = data
        _CACHE["ts"] = time.time()
        return True
    except Exception as e:
        print("[cloud_store] save error: " + type(e).__name__ + ": " + str(e))
        return False'''

    NEW_SAVE = '''def _save_gist(data: dict, retries: int = 3) -> bool:
    # PATCH_77: retry с backoff
    payload = {
        "files": {
            "wh40k_saves.json": {
                "content": json.dumps(data, ensure_ascii=False, indent=2),
            }
        }
    }
    last_err = None
    for attempt in range(retries):
        try:
            r = requests.patch(
                "https://api.github.com/gists/" + _GIST_ID,
                headers=_headers(),
                json=payload,
                timeout=15,
            )
            if r.status_code in (200, 201):
                _CACHE["data"] = data
                _CACHE["ts"] = time.time()
                return True

            # 5xx — retry, 4xx — нет
            if r.status_code >= 500:
                last_err = "HTTP " + str(r.status_code)
                print("[cloud_store] save attempt " + str(attempt + 1)
                      + " failed: " + last_err)
                time.sleep(1.0 * (attempt + 1))
                continue

            print("[cloud_store] PATCH fail: HTTP " + str(r.status_code)
                  + " " + r.text[:200])
            return False
        except requests.RequestException as e:
            last_err = type(e).__name__
            print("[cloud_store] save attempt " + str(attempt + 1)
                  + " exception: " + last_err)
            time.sleep(1.0 * (attempt + 1))

    print("[cloud_store] save failed after " + str(retries)
          + " attempts: " + str(last_err))
    return False'''

    if OLD_SAVE in text:
        nt = text.replace(OLD_SAVE, NEW_SAVE, 1)
        try:
            ast.parse(nt)
        except SyntaxError as e:
            r["errors"].append("cloud_store.py syntax: " + str(e))
        else:
            _bk(p)
            p.write_text(nt, encoding="utf-8")
            r["modified"].append("cloud_store.py — +retry с backoff")
    else:
        r["errors"].append("cloud_store.py: блок _save_gist не найден")


print("=== PATCH " + TAG + " ===")
for m in r["modified"]:
    print("  [MODIFIED] " + m)
for e in r["errors"]:
    print("  [ERROR] " + e)
print("DONE" if not r["errors"] else "DONE (with errors)")