# scripts/patch.py
# PATCH_16G — шестерня Механикум на ВСЕХ загрузочных экранах.
# Фразы остаются по фракции персонажа.
# Запуск: python scripts\patch.py
from __future__ import annotations

import ast
import shutil
import sys
from pathlib import Path

TAG = "PATCH_16G"
ROOT = Path(__file__).resolve().parent.parent
FILES: dict = {}


FILES["VERSION"] = "1.5.3\n"


# =====================================================================
# ui/loading_screen.py — заменить _sigil / _sigil_inline на mechanicum
# =====================================================================
def _patch_loading_sigils():
    p = ROOT / "ui" / "loading_screen.py"
    if not p.exists():
        return "ERROR: loading_screen.py not found"
    src = p.read_text(encoding="utf-8")
    if 'sigil_svg("mechanicum"' in src and "_sigil_theme" not in src:
        return "skip (already patched)"

    old1 = (
        'def _sigil(theme):\n'
        '    try:\n'
        '        from ui.assets import sigil_svg\n'
        '        return sigil_svg(theme or "dark", 140)\n'
        '    except Exception:\n'
        '        return ""\n'
    )
    new1 = (
        '# PATCH_16G — все загрузки используют шестерню Механикум.\n'
        '# Тема фракции остаётся для фраз, но не для иконки.\n'
        'def _sigil(theme):\n'
        '    try:\n'
        '        from ui.assets import sigil_svg\n'
        '        return sigil_svg("mechanicum", 140)\n'
        '    except Exception:\n'
        '        return ""\n'
    )
    if old1 not in src:
        return "ERROR: _sigil anchor not found"
    src = src.replace(old1, new1, 1)

    old2 = (
        'def _sigil_inline(theme):\n'
        '    try:\n'
        '        from ui.assets import sigil_svg\n'
        '        return sigil_svg(theme or "dark", 96)\n'
        '    except Exception:\n'
        '        return ""\n'
    )
    new2 = (
        'def _sigil_inline(theme):\n'
        '    try:\n'
        '        from ui.assets import sigil_svg\n'
        '        return sigil_svg("mechanicum", 96)\n'
        '    except Exception:\n'
        '        return ""\n'
    )
    if old2 not in src:
        return "ERROR: _sigil_inline anchor not found"
    src = src.replace(old2, new2, 1)

    try:
        ast.parse(src)
    except SyntaxError as e:
        return "ERROR SyntaxError: line " + str(e.lineno) + ": " + str(e.msg)
    bak = p.with_name(p.name + ".bak_pre_" + TAG)
    try:
        shutil.copy2(p, bak)
    except Exception as e:
        return "ERROR backup: " + type(e).__name__ + ": " + str(e)
    p.write_text(src, encoding="utf-8")
    return "backup + patched"


FILES["CHANGELOG.md"] = r"""# Changelog

Все значимые изменения проекта «Истории кота Баюна».

## [1.5.3] — 2026-09-24

### Changed

- **Шестерня Механикум на ВСЕХ загрузочных экранах.**
  Раньше в загрузке крутился символ темы игрока. Теперь — всегда
  Opus Machina. Логика: когитатор — это Механикум, он ведёт адепта
  от логина до первой сцены. Символ фракции появляется в игре.
- Фразы по-прежнему зависят от темы персонажа — дух-машины
  подстраивается под мир адепта.

## [1.5.2] — 2026-09-24

### Changed

- Визуал экрана «Развитие»: карточки характеристик, крупные цифры,
  подсветка профильных, единый стиль.

## [1.5.1] — 2026-09-24

### Fixed

- Русификация экрана «Развитие».

## [1.5.0] — 2026-09-24

### Added

- Универсальный экран загрузки: INITIATIO, wizard→game,
  продолжение из меню, inline-спиннер Мастера.
- Фразы по фракциям.
- Символ темы вместо шестерни Механикум.

## [1.4.5] — 2026-09-24

### Added

- Профильные характеристики для всех субфракций.

## [1.4.4] — 2026-09-24

### Fixed

- Русские имена навыков в карточке броска.

## [1.4.3] — 2026-09-24

### Fixed

- Кнопки БРОСИТЬ/ОТМЕНИТЬ не висят.

## [1.4.2] — 2026-09-24

### Added

- Интерактивный бросок d100.

## [1.4.1] — 2026-09-24

### Added

- Карточка броска (большая + компактная).
- 16 фракционных стилей.

### Fixed

- «Моржа» → «Степень успеха: N».

## [1.4.0] — 2026-09-24

### Added

- Мастер выдаёт XP за победу.
- Стартовый XP = 300.
- Кнопка «Развитие» в сайдбаре.

## [1.3.0] — 2026-09-24

### Added

- Секретные темы (код «АЛЬФА»).

## [1.2.0] — 2026-09-23

### Added

- Тема «Хаос».

## [1.1.0] — 2026-09-23

### Added

- Сиглы фракций, прокачка, INITIATIO.

## [1.0.0] — 2026-09-23

Первый полноценный релиз.
"""


def _write_one(rel_path, content):
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


def main():
    print("=" * 64)
    print("PATCH " + TAG + " — шестерня на всех загрузках")
    print("ROOT: " + str(ROOT))
    print("=" * 64)
    any_error = False

    print("[1/2] Файлы:")
    for rel in FILES:
        status = _write_one(rel, FILES[rel])
        if status.startswith("ERROR"):
            any_error = True
        print("  " + rel.ljust(34) + " -> " + status)

    print("[2/2] Точечные правки:")
    status = _patch_loading_sigils()
    if status.startswith("ERROR"):
        any_error = True
    print("  " + "loading_screen sigils".ljust(34) + " -> " + status)

    print("=" * 64)
    print("DONE" + (" (with errors)" if any_error else " — ok"))
    return 1 if any_error else 0


if __name__ == "__main__":
    sys.exit(main())