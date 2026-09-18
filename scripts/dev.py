"""Единый вход для разработки проекта.

Использование:
    python scripts/dev.py check   -- синтаксис + pytest (0 руб)
    python scripts/dev.py test    -- все pytest-тесты (0 руб)
    python scripts/dev.py live    -- живой прогон test_master.py (~0.15 руб)
    python scripts/dev.py info    -- состояние проекта
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _run(cmd: list[str]) -> int:
    print(f"\n$ {' '.join(cmd)}")
    return subprocess.call(cmd, cwd=str(ROOT))


def cmd_check() -> int:
    print("=== Синтаксис ===")
    files = sorted((ROOT / "core").glob("*.py")) + sorted((ROOT / "scripts").glob("*.py"))
    bad = 0
    for f in files:
        r = subprocess.run(
            [sys.executable, "-m", "py_compile", str(f)],
            capture_output=True, text=True,
        )
        if r.returncode != 0:
            print(f"[FAIL] {f.name}: {r.stderr.strip()}")
            bad += 1
    if bad == 0:
        print(f"[OK] {len(files)} файлов синтаксически чисты")
    else:
        print(f"[FAIL] {bad} файлов с ошибками")
    if bad:
        return 1
    print("\n=== pytest ===")
    return _run([sys.executable, "-m", "pytest", "tests/", "-v", "-q"])


def cmd_test() -> int:
    return _run([sys.executable, "-m", "pytest", "tests/", "-v"])


def cmd_live() -> int:
    print("Живой прогон test_master.py. Ожидаемая стоимость: ~0.15 руб.")
    ans = input("Продолжить? [y/N]: ").strip().lower()
    if ans != "y":
        print("Отменено.")
        return 0
    return _run([sys.executable, "tests/test_master.py"])


def cmd_info() -> int:
    print(f"Проект: {ROOT}")
    core = sorted((ROOT / "core").glob("*.py"))
    print(f"core/: {len(core)} модулей")
    tests = sorted((ROOT / "tests").glob("test_*.py"))
    print(f"tests/: {len(tests)} тестовых файлов")
    for f in tests:
        print(f"  - {f.name}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Dev-скрипты проекта")
    ap.add_argument("command", choices=["check", "test", "live", "info"])
    args = ap.parse_args()
    return {
        "check": cmd_check,
        "test": cmd_test,
        "live": cmd_live,
        "info": cmd_info,
    }[args.command]()


if __name__ == "__main__":
    sys.exit(main())