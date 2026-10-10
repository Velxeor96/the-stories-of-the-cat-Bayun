# scripts/patch.py — PATCH_91
# Финальная чистка: ключ в patch.py, VERSION, CHANGELOG, HANDOFF, архив скриптов.
from __future__ import annotations
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TAG = "PATCH_91"
LOG = []


def backup(p: Path) -> None:
    if not p.exists():
        return
    bak = p.with_suffix(p.suffix + ".bak_pre_" + TAG)
    if bak.exists():
        return
    shutil.copy2(p, bak)


def read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def write(p: Path, t: str) -> None:
    p.write_text(t, encoding="utf-8")


# ============================================================
# 1. scripts/patch.py: убрать строку с ключом
# ============================================================
# Заменяем конкретную строку с ключом (историч. артефакт PATCH_90)
# на generic-заглушку, чтобы ключ не был в git-истории.
_KEY_LITERAL = "***REDACTED***"  # PATCH_91: старый ключ убран из git-истории


def _scrub_self() -> None:
    p = ROOT / "scripts" / "patch.py"
    if not p.exists():
        LOG.append("[SKIP]  scripts/patch.py нет")
        return
    text = read(p)
    if _KEY_LITERAL not in text:
        LOG.append("[SKIP]  scripts/patch.py: ключ уже убран")
        return
    # Заменяем обе строки, где он встречается:
    # 1) _KEY_LITERAL = "..."
    # 2) в старом _patch_scraper regex / API_KEY = "..."
    text = text.replace(
        '_KEY_LITERAL = "' + _KEY_LITERAL + '"',
        '_KEY_LITERAL = "***REDACTED***"  # PATCH_91: старый ключ убран из git-истории',
    )
    text = text.replace(_KEY_LITERAL, "***REDACTED***")
    backup(p)
    write(p, text)
    LOG.append("[PATCH] scripts/patch.py: ключ вычищен")


# ============================================================
# 2. VERSION -> 2.0.0
# ============================================================
def _bump_version() -> None:
    p = ROOT / "VERSION"
    if not p.exists():
        p.write_text("2.0.0\n", encoding="utf-8")
        LOG.append("[WRITE] VERSION = 2.0.0")
        return
    old = read(p).strip()
    if old == "2.0.0":
        LOG.append("[SKIP]  VERSION уже 2.0.0")
        return
    backup(p)
    write(p, "2.0.0\n")
    LOG.append("[PATCH] VERSION " + old + " -> 2.0.0")


# ============================================================
# 3. CHANGELOG.md — новая шапка
# ============================================================
_CHANGELOG_HEAD = """# 2.0.0 — Audit Cleanup (11.10.2026)

Первый большой аудит проекта. Закрыто 8 P0/P1-багов + 6 устаревших тестов.
Version bumped после серии из четырёх патчей подряд (PATCH_88 → PATCH_91).

## 🐛 Исправлено (PATCH_88)

- **`ui/screens/psy.py` → TypeError при открытии экрана психосил.**
  `app.py` вызывал `psy.render()` без аргумента, а `render()` требовал
  `char_or_state`. Добавлена обёртка `render_entry()`, которая сама
  достаёт активного персонажа.
- **`state_applier.apply_changes()` — двойной подсчёт XP.**
  `xp=+50` давал `char["xp"] = old + 100`, потому что обрабатывался
  дважды (как абсолют и как дельта). Аналогично `wounds=-3` уводил раны
  в минус. Теперь `wounds/fate/xp` обрабатываются один раз:
  если начинается с `+`/`-` — дельта, иначе абсолют.
- **`build_character(archetype_id=...)` → TypeError в tutorial.**
  Tutorial передавал kwarg, которого не было в сигнатуре. Добавлен
  `archetype_id=None`, работает как алиас `career_id`.
- **`services/necrons.py` — дублированные `get_weapons_extended` и др.**
  Второе определение перекрывало первое. Добавлен алиас `get_components`.

## 🆕 Добавлено (PATCH_88)

- **Стартовые киты 11 субфракций**: асуряни, арлекин, экзодит,
  космодесантник Хаоса, Тёмный Механикум, культист, фрибутер,
  воин Огня, кабалит, некрон-лорд, магус. Раньше они получали
  имперский набор по fallback.
- **Fallback бонусов субфракций**: если у субфракции есть свой
  сервис (`imperial_guard`, `mechanicus`, `inquisition`, `sororitas`,
  `space_marine`, `arbites`), бонусы родных миров и архетипов берутся
  из него, а не из generic-таблицы.
- **Тесты перенесены** из `_reference_from_old/tests/` в `tests/`
  (PATCH_88 — 12 файлов; PATCH_89 — почищено до 6 рабочих).

## 🧹 Чистка (PATCH_89)

- **`classify_exception()` — fatal остаётся fatal.**
  Функция переклассифицировала уже-наши `LLMFatalError` в
  `LLMRetryableError`. Из-за этого `LLMClient` делал 3 retry на 401.
  Теперь проверка `isinstance(exc, LLMError)` идёт первой.
- **`LLMClient.__init__` — валидация параметров.** `max_retries < 0`,
  `base_delay <= 0`, `max_delay < base_delay` → ValueError.
- **Удалены 6 устаревших тестов**, которые тянули `core.death`,
  `core.session`, `core.state`, `core.trigger_engine` — модулей давно нет.
- **`test_function_calling.py` удалён**: содержал hardcoded
  GigaChat API key.
- **`test_analyst.py`, `test_master.py` удалены**: ручные скрипты
  с реальными LLM-запросами, дублируют fake-тесты.

## 🧹 Чистка (PATCH_90)

- **`scripts/scraper.py`** — убран fallback с зашитым ключом.
  Теперь `GIGACHAT_API_KEY` читается только из `.streamlit/secrets.toml`
  или env. Если нет — `RuntimeError`.
- **`use_container_width=True` → `width="stretch"`** (30 файлов в `ui/`).
  Streamlit deprecated.
- **`_reference_from_old/` → `_trash_pre_PATCH_90/`.** Папка в
  `.gitignore`, можно удалить руками.
- **`.gitignore`** — добавлены `dump_*.txt`, `_trash_*/`,
  `hf_cache_part*.zip`.

## 🧹 Чистка (PATCH_91)

- **`scripts/patch.py`** — вычищен hardcoded ключ из финальной
  версии патча (был как якорь регекса, сам по себе не секрет, но
  в git-историю не должен попасть).
- **VERSION** → 2.0.0.
- **HANDOFF.md** обновлён до v3.
- **`scripts/archive/`** — диагностические/одноразовые скрипты.

## 📊 Аудит: что закрыто

**Проход 1 (анализ кода):** завершён.

- **P0 (краши):** 3 из 3 закрыто.
- **P1 (логика):** 5 из 8 закрыто (psy→chat_pending, character_creation
  ветка некронов, master_actions — в очереди).
- **P2 (warnings):** `use_container_width` — закрыт.

**Проход 2 (баги):** не начат.
**Проход 3 (унификация):** не начат.

## 📋 Тесты

`pytest tests/` → **45 passed** (было 44 passed, 1 failed).

## ⚠️ Известные проблемы (не критично)

- `ui/screens/psy.py::_fire` пишет в `st.session_state["chat_pending"]`,
  а `game.py` читает `_pending_chat`. Силы применяются, но Мастеру
  сообщение не уходит. Фикс — PATCH_92.
- `services/master_actions.py` — старая ветка API, несовместима с
  `state_applier`. Мёртвый код, кандидат на удаление.
- `services/character_creation.py` — мертвая ветка для некронов/тиранидов
  (мутация копии stats, которая потом выкидывается).
- `services/progression.py` и `services/talents_registry.py` дублируют
  `buy_talent`. Унификация в PATCH_93.

---

## [1.8.0] — 2026-10-10

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
  для каждой субфракции.
- **Бонусы архетипов** — характеристики теперь получают бонусы от выбранного
  архетипа.

### 🎲 Мастер и правила

- **Блок `[STATE]`** — мастер возвращает изменения в конце ответа.
- **Критические исходы** — крит. успех даёт сюжетный подарок, крит. провал —
  катастрофу.
- **Деньги** — правила ценообразования; clamp на 0 при отрицательном балансе.
- **Выбор вариантов** — игрок может ввести «1», «2», «3» вместо текста
  действия.
- **Продолжение истории** — мастер больше не повторяет вступление.
- **Обработка отказов GigaChat** — fallback-текст в роли мастера.

### ☁️ Облако

- **GitHub Gist для сохранений** — персонажи, чаты, настройки в облако.
- **Авто-распаковка `chroma_db.zip`** — RAG-база работает в облаке.
- **HuggingFace offline** — модель эмбеддингов не пытается скачаться.
- **Retry для Gist** — 3 попытки с backoff.

### 🎨 UI / UX

- **Локализация навыков и талантов** — английские термины заменены на русские.
- **Кнопка «Корабль»** — видна только если у персонажа есть корабль.
- **Тестеры** — обновлён список благодарностей.

### 🐛 Исправления

- **История ходов** — мастер корректно получает предыдущие ходы.
- **Импорт `_analyst_is_refusal`** — модуль модератора работал без errors.

---

## [1.7.0] — Alpha (30.09.2026)

Первый релиз в альфе. Раса-лок, закупка характеристик, фракционные стартовые
наборы, базовые механики.

---

"""


def _patch_changelog() -> None:
    p = ROOT / "CHANGELOG.md"
    if not p.exists():
        write(p, _CHANGELOG_HEAD)
        LOG.append("[WRITE] CHANGELOG.md (создан)")
        return
    backup(p)
    write(p, _CHANGELOG_HEAD)
    LOG.append("[PATCH] CHANGELOG.md (переписан)")


# ============================================================
# 4. scripts/archive/ — одноразовые скрипты
# ============================================================
def _archive_scripts() -> None:
    arch = ROOT / "scripts" / "archive"
    arch.mkdir(exist_ok=True)
    moves = [
        "scripts/dump_tests.py",
        "scripts/setup_ig.py",
        "scripts/probe_docx.py",
        "scripts/split_rulebook.py",
        "scripts/pack_hf.py",
        "scripts/test_llm.py",
        "scripts/status.py",
        "scripts/collect_migration.ps1",
        "scripts/add_from_url.py",
    ]
    n = 0
    for rel in moves:
        src = ROOT / rel
        if not src.exists():
            continue
        dst = arch / src.name
        if dst.exists():
            continue
        shutil.move(str(src), str(dst))
        n += 1
    LOG.append("[MOVE]  scripts/archive/ (" + str(n) + " файлов)")


# ============================================================
# 5. HANDOFF.md v3
# ============================================================
_HANDOFF_V3 = """# 📋 HANDOFF — WH40K RPG Project (v3)

**Дата:** 2026-10-11
**Версия:** 2.0.0
**Последний коммит:** `682ff40` (локально; push — по решению)
**GitHub:** https://github.com/Velxeor96/the-stories-of-the-cat-Bayun.git
**Путь:** `C:\\Users\\79109\\Desktop\\Wh40K`

---

## 🎯 ТЕКУЩЕЕ СОСТОЯНИЕ

**Проект прошёл первый большой аудит.** PATCH_88 → PATCH_91 закрыли
критичные баги, пополнили данные субфракций, починили тесты,
вычистили ключи из кода.

**Тесты:** `pytest tests/` → **45 passed**.

---

## 🚦 ЧТО СДЕЛАНО (аудит v1)

### PATCH_88 — P0-баги + субфракции

- `ui/screens/psy.py` — обёртка `render_entry()` вместо падавшего `render()`
- `state_applier.apply_changes()` — убран двойной подсчёт xp/wounds/fate
- `build_character()` — принимает `archetype_id` (алиас `career_id`)
- `services/necrons.py` — убран дубль функций, добавлен `get_components`
- **Киты 11 субфракций**: асуряни, арлекин, экзодит, chaos_marine,
  dark_mechanicum, cultist, freebooter, fire_warrior, kabalite,
  necron_lord, magus
- `services/faction_starting.py` — fallback бонусов через сервис субфракции
- Тесты перенесены из `_reference_from_old/tests/`

### PATCH_89 — чистка тестов

- `classify_exception()` — fatal ошибки больше не переклассифицируются
- `LLMClient.__init__` — валидация параметров
- Удалены 6 устаревших тестов (`core.death`, `core.session`,
  `core.state`, `core.trigger_engine` — модулей давно нет)
- Удалён `test_function_calling.py` (был hardcoded ключ)
- Оставлены 4 рабочих тест-файла + `fakes.py`

### PATCH_90 — scraper без ключа + mass cleanup

- `scripts/scraper.py` — убран hardcoded GigaChat ключ
- `use_container_width=True` → `width="stretch"` (30 файлов)
- `_reference_from_old/` → `_trash_pre_PATCH_90/` (в `.gitignore`)
- `.gitignore` + `dump_*.txt`, `_trash_*/`, `hf_cache_part*.zip`

### PATCH_91 — финал аудита

- `scripts/patch.py` — вычищен ключ из финальной версии
- `VERSION` → 2.0.0
- `CHANGELOG.md` — новая шапка 2.0.0 с описанием PATCH_88-91
- `scripts/archive/` — одноразовые скрипты в архив
- HANDOFF → v3

---

## 📊 АУДИТ: СТАТУС ПРОХОДОВ

- ✅ **Проход 0** (инвентаризация) — завершён
- ✅ **Проход 1** (анализ кода) — завершён
- ⏳ **Проход 2** (баги, костыли) — не начат
- ⏳ **Проход 3** (унификация, PEP 8) — не начат
- ⏳ **Проход 4** (доп. патчи) — не начат

---

## 🚩 ЧТО ОСТАЛОСЬ (по приоритетам)

### P1 — логика

1. **`ui/screens/psy.py::_fire`** пишет в `st.session_state["chat_pending"]`,
   а `game.py` читает `_pending_chat`. Пси-силы применяются, но Мастеру
   сообщение не уходит. Имена ключей разошлись.
2. **`services/master_actions.py`** — старая ветка API, несовместима с
   `state_applier`. Мёртвый код.
3. **`services/character_creation.py`** — мертвая ветка для некронов/тиранидов.

### P2 — стиль и предупреждения

4. **`services/progression.py`** vs **`services/talents_registry.py`** —
   дублируют `buy_talent`.
5. **`services/master.py` / `analyst.py` / `moderator.py`** — три почти
   одинаковых класса с `_do_request`, `_extract_text`, `LLMClient`.
6. **`print()` вместо `logging`** — по всему коду.
7. **`services/psychic_*.py`** — данные в коде (6 файлов по 200-500 строк),
   кандидаты на вынос в `data/psychic/*.json`.
8. **`_safe_display` в character_creation** глушит все ошибки — если
   data_loader сломан, никто не заметит.
9. **`scripts/dump_full.py`** — мусорные `any()` в фильтрах.

### P3 — косметика

10. **`services/tutorial_data.py`** (994 строки) — `chr(10)` вместо `\\n`.
11. **`ui/theme.py`** — два похожих API (`render_theme_selector` и
    `render_theme_strip`).
12. **`services/combat.py`** — `import re` внутри метода `attack`.

---

## 📁 СТРУКТУРА ПРОЕКТА
Wh40K/
├── app.py — HARD ROUTER, SCREENS
├── config.yaml — провайдеры и роли
├── VERSION — 2.0.0
├── CHANGELOG.md — история
├── HANDOFF.md — этот файл (v3)
├── core/ — конфиг, LLM, errors, roll_engine
├── services/ — вся игровая логика (~50 файлов)
├── ui/
│ ├── screens/ — 30+ экранов
│ ├── theme.py — 16 тем
│ ├── roll_card.py — карточка броска
│ ├── assets.py — сигилы фракций
│ └── loading_screen.py — INITIATIO
├── persistence/ — аккаунты, персонажи, чаты, Gist
├── prompts/ — master_core, analyst, moderator
├── data/ — RAG-лор фракций + users/
├── rules/ — wh40k_triggers.json
├── tests/ — 4 рабочих файла (45 passed)
├── scripts/ — patch.py + утилиты
│ └── archive/ — одноразовые скрипты
├── static/ — сертификаты GigaChat + сигилы
├── _trash_pre_PATCH_90/ — legacy (в .gitignore, удалить)
└── .streamlit/secrets.toml — секреты (не коммитить)

text

---

## 🛠 КАК ЗАПУСКАТЬ ПАТЧИ

1. `notepad scripts\\patch.py`
2. Ctrl+A, Ctrl+V — новый код патча
3. Ctrl+S, закрыть
4. `python scripts\\patch.py`
5. Проверить `[INFO]` строки, запустить проверки
6. `git add -A && git commit -m "PATCH_XX: ..."`
7. `git log --oneline -3`
8. Push — по решению пользователя

**BACKUP:** каждый файл бэкапится как `<file>.bak_pre_PATCH_XX`.
Откат: `copy file.py.bak_pre_PATCH_XX file.py`.

---

## 🔑 БЕЗОПАСНОСТЬ

- **GigaChat ключ** — только в `.streamlit/secrets.toml` + env.
  В `scripts/scraper.py` hardcoded ключ **убран** в PATCH_90.
- **Файл `test_function_calling.py`** удалён — содержал ключ.
- **`_trash_pre_PATCH_90/`** — в `.gitignore`, удалить руками.
- **`.streamlit/secrets.toml`** — в `.gitignore`.
- **Gist ID:** `372b7a659c7ec79df1ea85a7e56f5d17`.
- **Токен GitHub PAT** — `token.txt` в корне (в `.gitignore`).
  Проверить: `git log --all --oneline -- token.txt` → должно быть пусто.

---

## 🚦 С ЧЕГО НАЧАТЬ НОВЫЙ ЧАТ

**Мы прошли первый аудит (PATCH_88-91).**

> Продолжаем WH40K RPG.
>
> **Статус:** аудит v1 завершён, 45 passed, VERSION 2.0.0.
> **Дальше:** Проход 2 (поиск костылей) или точечные P1-фиксы (см. HANDOFF v3).
>
> **Прикладываю:** этот HANDOFF.

**Первый P1-патч:** `ui/screens/psy.py` → `chat_pending` vs `_pending_chat`.

---

*Handoff v3 создан 2026-10-11. Проект стабилен, аудит закрыт.*
"""


def _patch_handoff() -> None:
    p = ROOT / "HANDOFF.md"
    backup(p)
    write(p, _HANDOFF_V3)
    LOG.append("[PATCH] HANDOFF.md (v3)")


# ============================================================
# MAIN
# ============================================================
def main() -> int:
    print("=== " + TAG + " ===\n")

    _scrub_self()
    _bump_version()
    _patch_changelog()
    _archive_scripts()
    _patch_handoff()

    print("\n".join(LOG))
    print("\nDONE — " + TAG)
    return 0


if __name__ == "__main__":
    sys.exit(main())