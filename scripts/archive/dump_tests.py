# scripts/dump_tests.py — дамп содержимого tests/*.py
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
tests = ROOT / "tests"
out = ROOT / "dump_tests.txt"

files = sorted(p for p in tests.glob("*.py") if p.name != "__init__.py")
print("[dump] файлов: " + str(len(files)))

with out.open("w", encoding="utf-8") as f:
    f.write("# TESTS DUMP — " + str(ROOT) + "\n")
    f.write("# files: " + str(len(files)) + "\n")
    f.write("=" * 80 + "\n\n")
    for p in files:
        try:
            txt = p.read_text(encoding="utf-8")
        except Exception as e:
            f.write("### FILE: " + p.name + "\n[ERROR " + str(e) + "]\n\n")
            continue
        rel = p.relative_to(ROOT).as_posix()
        f.write("### FILE: " + rel + "\n")
        f.write("### CHARS: " + str(len(txt))
                + "  LINES: " + str(txt.count(chr(10)) + 1) + "\n")
        f.write("-" * 80 + "\n")
        f.write(txt if txt.endswith("\n") else txt + "\n")
        f.write("-" * 80 + "\n\n")

print("[OK] " + str(out))