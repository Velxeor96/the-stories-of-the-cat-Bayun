# 📋 HANDOFF: WARHAMMER 40K RPG PLATFORM

**Дата:** 2026-09-20 (утро, после ночной сессии)
**Версия:** 1.4
**Статус:** Спринт 1 закрыт 7/8. Баг иконок локализован, фикс в работе.

---

## 🎯 ВИДЕНИЕ

**Что строим:** Платформа для текстовых RPG с мульти-ИИ Мастером.
**Пилот:** Warhammer 40,000 Rogue Trader.
**Принцип:** максимум логики на Python, нейронка — только Мастер.

---

## 🏗️ АРХИТЕКТУРА

**Главный принцип:** состояние, правила, броски, эффекты — в Python.
LLM только парсит фразу (Analyst), пишет нарратив (Master),
и проверяет спорные случаи модерации.

**Схема хода:**
Игрок → Moderator.check() → [regex ALLOW/RESHAPE/REJECT]
↓ (если ALLOW)
Analyst.parse() → ParsedCommand (JSON)
↓
roll_engine.check() → RollResult (Python, не LLM)
↓
trigger_engine.fire() → эффекты
↓
Master.narrate() → текст (единственный LLM-вызов)
↓
apply_turn_effects() → автоначисление XP/ран/репутации
↓
ensure_action_variants() → гарантированные варианты

text

**Мультимодельность (КРИТИЧНО для миграции):**
- В `config.yaml` роли: `analyst`, `master`, `moderator`, `rag`.
- `core/config.py` → `config.role_model("master")` отдаёт `.provider` и `.id`.
- `core/llm_client.py` — универсальный, работает с любым OpenAI-совместимым API.
- Смена провайдера = одна строка в `config.yaml`.

**Что уже переведено на Python (не LLM):**
- Все броски (`roll_engine.check`)
- Триггеры и эффекты (`trigger_engine`)
- Смерть, статусы (`death`)
- Модерация regex-слоем (до LLM)
- Варианты действий (`variants.ensure_action_variants`)
- Профиль персонажа в контекст (`orchestrator`)
- RAG-контекст ChromaDB

**Что на LLM (минимизировано):**
- Analyst: фраза → JSON
- Master: нарратив
- Moderator LLM-слой: только спорные случаи

---

## 🖥️ СТЕК

- Python 3.13, Streamlit 1.63
- ChromaDB (4624 чанка), sentence-transformers (multilingual-e5-small)
- openai SDK, torch 2.6+cu124 (GTX 1660)

**Путь:** `C:\Users\79109\Desktop\my_game\`
**GitHub:** https://github.com/Velxeor96/the-stories-of-the-cat-Bayun
**Streamlit:** https://the-stories-of-the-cat-bayun-rpg.streamlit.app

**Провайдер сейчас:** KodikRouter / deepseek-v4-flash-latest
**Провайдер для миграции:** GigaChat-2-Pro (ключ уже есть в `.streamlit/secrets.toml`)

---

## 📁 СТРУКТУРА
my_game/
├── core/
│ ├── state.py, roll_engine.py, trigger_engine.py, death.py
│ ├── errors.py, llm_client.py, config.py
│ ├── auth.py (регистрация/вход)
│ ├── analyst.py, master.py (max_tokens=700), moderator.py
│ ├── orchestrator.py (принимает extra_context)
│ ├── variants.py, session.py
├── ui_themes.py (22 темы, шрифты = Georgia/Consolas)
├── ui_render.py (CSS, _inject_ghost_kill отключён патчем 44)
├── ui_state.py (StateAdapter + эффекты)
├── app.py (166378 символов, восстановлен из .bak38)
├── rules/wh40k_triggers.json
├── prompts/master_core.txt, moderator.txt, analyst.txt
├── scripts/dev.py, scripts/patch.py
├── tests/ (44 passed)
├── characters/Костопевец.json
├── data/accounts/, data/users/
├── config.yaml
├── .streamlit/secrets.toml (KODIK_API_KEY, GIGACHAT_API_KEY)
├── HANDOFF.md ← ЭТОТ ФАЙЛ

text

---

## ✅ ЧТО РАБОТАЕТ

- Ядро (state, броски, триггеры, смерть, LLM-клиент, ошибки).
- Analyst / Master / Moderator / Orchestrator / Session.
- Auth (регистрация, вход, изоляция данных).
- Splash + Onboarding (тексты читаемы).
- Wizard персонажа, пол строго 2 варианта.
- 22 темы, DEFAULT_THEME = inquisition (чёрно-красная).
- PRO-эффекты: XP, порча, деньги, повышение ранга.
- RAG (ChromaDB) + профиль персонажа в extra_context.
- Карточки предметов «ПОЛУЧЕНО В ИНВЕНТАРЬ».
- Fallback мастера (logs/errors.log).
- 44 pytest-тестов, 0 warnings.
- Баланс KodikRouter: 498,79 ₽ (потрачено ~1,21 ₽).

---

## 🔴 ГЛАВНЫЙ БАГ — ИКОНКИ EXPANDER

**Симптом:** Заголовки expander выглядят как «arrИво ...» поверх текста.
Например: `arrИво exactly` вместо `Что такое НРИ?`.

**ПРИЧИНА НАЙДЕНА:** патч 38 удалил **все** `@import url("https://fonts.googleapis.com/...")`
из `ui_render.py`. Вместе с ними убрался `@import` для **Material Symbols**,
которые Streamlit использует для иконок expander.

Streamlit рендерит иконку expander как `<span class="material-symbols-rounded">keyboard_arrow_right</span>`.
Если шрифт Material Symbols не загружен, браузер показывает **буквы лигатуры**:
«keyboard_arrow_right» → «arrИво».

**ФИКС (готов к применению):**

В `ui_render.py` в функции `render_theme()` **вернуть** `@import` **только** для Material Symbols:

```python
def render_theme(theme_key: str) -> None:
    # ВЕРНУТЬ ИКОНКИ Streamlit (Material Symbols)
    st.markdown(
        '<style>@import url("https://fonts.googleapis.com/css2?'
        'family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200");'
        '</style>',
        unsafe_allow_html=True,
    )
    # ... остальной код
Если Google Fonts блокируется из РФ — скачать woff2 локально:

text
static/fonts/MaterialSymbolsRounded.woff2
и подложить через @font-face:

css
@font-face {
    font-family: 'Material Symbols Rounded';
    src: url('/app/static/fonts/MaterialSymbolsRounded.woff2') format('woff2');
}
Или в крайнем случае: заменить все st.expander в app.py на st.container(border=True)
с обычным <h4> — иконки не нужны, ghost исчезнет как класс.

Что уже сделано в попытках:

Патчи 39-42 — CSS override, не помогло.

Патч 44 — отключён наш _inject_ghost_kill(), стало видно чистую причину.

Патч 43 — упал (не записался), но диагностика сработала.

Все бэкапы целы.

Проверить в начале новой сессии:

findstr /N "material-symbols" ui_render.py — есть ли в CSS.

findstr /N "@import" ui_render.py — есть ли хоть один @import.

findstr /N "fonts.googleapis" ui_render.py — есть ли упоминания.

🎯 ПЛАН РАБОТЫ (в порядке приоритета)
1. Фикс иконок (30 минут)
Вернуть @import Material Symbols в ui_render.py. Прогнать dev.py run, Ctrl+F5, скрин.

Если не сработает — заменить st.expander на st.container(border=True) в:

render_onboarding (app.py)

_render_auth_gate (app.py, уже сделано патчем 40)

render_character_sidebar (там expander'ы ПРОВЕРКИ / ДЕЙСТВИЯ / ПОМОЩЬ)

2. Миграция на GigaChat (20 минут)
Один патч:

config.yaml: у ролей analyst, master, moderator → provider: gigachat, model: GigaChat-2-Pro.

core/config.py: убедиться, что провайдер gigachat есть.

API-ключ уже в .streamlit/secrets.toml → GIGACHAT_API_KEY.

Для будущей миграции обратно: сделать в config.yaml параметр default_provider,
чтобы переключаться одной строкой.

3. Тестовый модуль (1-2 часа)
core/tutorial.py + prompts/tutorial.txt.

Сценарий:

Игрок просыпается на корабле, осматривается.

Мастер говорит: «Брось проверку Внимания» (проверяет броски).

Игрок находит предмет, берёт его (проверяет карточку ПОЛУЧЕНО).

Разговор с NPC (проверяет talk).

Переход в другую локацию (проверяет location=).

Финальный экран: «Ты прошёл обучение».

В конце session.tutorial_mode = False, обычная игра.

4. Механики — что допиливать?
Пользователь должен уточнить. Кандидаты:

Начисление урона/порчи в разных бросках.

Трата денег (пока не работает).

Расход предметов (стимулянт, аптечка уже частично).

Обновление корабля.

Изменение репутации.

5. Картинки (когда механики стабильны)
Stable Diffusion локально (GTX 1660 / 6GB — SD 1.5, SDXL Turbo).

Или Kandinsky 3.1 (Сбер).

📝 ФОРМАТ РАБОТЫ
Правила:

Новый файл или правка → только через scripts/patch.py.

notepad scripts\patch.py, Ctrl+A, Ctrl+V, Ctrl+S, закрыть.

python scripts\patch.py

python scripts\dev.py check — должно быть 44 passed.

Не переходить дальше, пока не подтверждено.

Push — только по команде «пушим».

Счётчик чата в конце каждой реплики.

Не вставлять ключи в чат.

После патча CSS — ЗАКРЫТЬ Streamlit (Ctrl+C) и запустить заново,
потом в браузере Ctrl+F5. Иначе CSS из кэша.

⚠️ Уроки:

re.sub с \s+ склеивает код через переводы строк → использовать [ \t]+.

Удаление @import googleapis.com ломает Material Symbols — иконки
превращаются в буквы. Никогда не удалять этот @import целиком.

* { } селекторы в CSS ломают Material Symbols. Не использовать.

st.expander в app.py требует живых Material Symbols. Если шрифт
не загружен — будут буквы вместо иконок.