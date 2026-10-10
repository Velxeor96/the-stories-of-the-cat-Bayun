# 📋 HANDOFF — WH40K RPG Project (v3)

**Дата:** 2026-10-11
**Версия:** 2.0.0
**Последний коммит:** `682ff40` (локально; push — по решению)
**GitHub:** https://github.com/Velxeor96/the-stories-of-the-cat-Bayun.git
**Путь:** `C:\Users\79109\Desktop\Wh40K`

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

10. **`services/tutorial_data.py`** (994 строки) — `chr(10)` вместо `\n`.
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

1. `notepad scripts\patch.py`
2. Ctrl+A, Ctrl+V — новый код патча
3. Ctrl+S, закрыть
4. `python scripts\patch.py`
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
