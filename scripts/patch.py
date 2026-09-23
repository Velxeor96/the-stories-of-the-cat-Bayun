# scripts/patch.py
# PATCH_15V — релиз 1.1.0: сводный CHANGELOG + VERSION.
#   VERSION     — 1.1.0
#   CHANGELOG.md — полная история до 1.1.0
# Запуск: python scripts\patch.py
from __future__ import annotations

import ast
import shutil
import sys
from pathlib import Path

TAG = "PATCH_15V"
ROOT = Path(__file__).resolve().parent.parent
FILES: dict[str, str] = {}


FILES["VERSION"] = "1.1.0\n"


FILES["CHANGELOG.md"] = r"""# Changelog

Все значимые изменения проекта «Истории Кота Баюна».
Формат: Keep a Changelog. Версии: [MAJOR.MINOR.PATCH].

## [1.1.0] — 2026-09-23

Первый минорный релиз после 1.0.0. Визуал фракций, INITIATIO,
прозрачные сиглы, тема Хаос.

### Added

- **Тема «Хаос».** Кроваво-красная палитра + 8-конечная звезда
  Неделимого. Сигл `static/sigils/chaos.png`.
- **Правовая плашка** на splash-экране: фан-проект, некоммерческий,
  все права у Games Workshop Ltd.
- **Экран «Что нового».** Модалка при первом входе после обновления
  + кнопка в главном меню. `CHANGELOG.md` в настройках, вкладка
  «История версий».
- **Система прокачки Rogue Trader.** Ранги по потраченному XP,
  апгрейды характеристик (Simple/Intermediate/Trained/Expert),
  навыки (Trained/Experienced/Veteran), таланты, психосилы.
  Отдельный экран «Развитие».
- **Сайдбар игры.** Локация, полоски HP/Судьба/XP с пульсацией,
  экипировка (4 слота + рюкзак), оружие с интерактивными атаками
  через модалку, навыки, психосилы.
- **Экран INITIATIO.** Вращающаяся шестерня, прогресс-бар,
  100 случайных фраз Механикум, автопрогресс ~10 сек.
- **Логика landing-guard.** Свежий логин больше не проваливается
  в «зависший» wizard прошлой сессии.

### Changed

- **Сиглы фракций из PNG/SVG.** `ui/assets.py` читает
  `static/sigils/<theme>.png` или `.svg` с диска.
- **PNG-сиглы красятся в акцент темы** через SVG `feColorMatrix`
  (RGB = accent, alpha = 1 − luminance). Никаких белых/чёрных
  квадратов — символ ложится прямо на фон.
- **INITIATIO всегда после логина.** Убрана проверка `loading_seen`
  из landing-логики. Каждый вход в аккаунт даёт
  `auth → kot_intro → INITIATIO → main_menu`.
- **Символ INITIATIO — mechanicum.** Берётся из
  `static/sigils/mechanicum.png`.
- `git push` дополнительно несёт статику фракций (PNG), служебные
  README и маркеры патчей.

### Fixed

- **Проверка сигнатуры PNG.** Если файл в `static/sigils/` не PNG
  по содержимому — отбрасывается в fallback, лог `[assets]`.
- **SVG-fallback Эльдар** — «Глаз Иши»: стилизованный эльдарский
  глаз со слезой (используется, если `eldar.png` отсутствует).
- **Таймауты GigaChat.** OAuth: connect=10s, read=30s.
  Chat: connect=10s, read=120s. Подробные `[gigachat]`-логи.
- **Отключён file watcher Streamlit** — убирает спам от `transformers`.
- **`_resolve_screen`** корректно фиксирует `screen` в `session_state`
  на каждом rerun.

### Known issues

- Мастер может «задумываться» до 2 минут на сложных ходах — GigaChat.
- Drag-n-drop инвентаря невозможен — ограничение Streamlit.
- Горячая перезагрузка `.streamlit/config.toml` не работает,
  нужен перезапуск процесса.

## [1.0.0] — 2026-09-23

Первый полноценный релиз. Играбельная WH40K RPG с Мастером-ИИ.

### Added

- Создание персонажа: 8 фракций (Империум, Хаос, Эльдары, Друкхари,
  Орки, Тау, Некроны, Генокрады), субфракции, архетипы, характеристики.
- Мастер-чат: GigaChat, модератор, аналитик намерений, RAG по
  7234 чанкам лора.
- Броски d100: 9 сложностей, критические успехи/провалы,
  4 варианта карточки.
- Туториал «Потент» — 6 заскриптованных сцен.
- Экран «Создатели» с благодарностями тестерам.
- Настройки: выбор темы, логи чата, отладка, сброс вводного потока.
- 3 базовые темы: Нейтральная, Империум, Механикум.
"""


def _write_one(rel_path: str, content: str) -> str:
    dst = ROOT / rel_path
    dst.parent.mkdir(parents=True, exist_ok=True)
    existed = dst.exists()
    if existed:
        try:
            old = dst.read_text(encoding="utf-8")
        except Exception as e:
            return "ERROR reading: " + type(e).__name__ + ": " + str(e)
        if old == content:
            return "skip (identical)"
    if dst.suffix == ".py":
        try:
            ast.parse(content)
        except SyntaxError as e:
            return ("ERROR SyntaxError: line " + str(e.lineno)
                    + ": " + str(e.msg))
    if existed:
        bak = dst.with_name(dst.name + ".bak_pre_" + TAG)
        try:
            shutil.copy2(dst, bak)
        except Exception as e:
            return "ERROR backup: " + type(e).__name__ + ": " + str(e)
    try:
        dst.write_text(content, encoding="utf-8")
    except Exception as e:
        return "ERROR write: " + type(e).__name__ + ": " + str(e)
    return "backup + overwrite" if existed else "create"


def main() -> int:
    print("=" * 64)
    print("PATCH " + TAG + " — релиз 1.1.0")
    print("ROOT: " + str(ROOT))
    print("=" * 64)

    any_error = False
    for rel in FILES:
        status = _write_one(rel, FILES[rel])
        if status.startswith("ERROR"):
            any_error = True
        print("  " + rel.ljust(30) + " -> " + status)

    print("=" * 64)
    print("DONE" + (" (with errors)" if any_error else " — ok"))
    return 1 if any_error else 0


if __name__ == "__main__":
    sys.exit(main())