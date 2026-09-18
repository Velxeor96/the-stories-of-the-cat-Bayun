"""Единый патчер проекта."""

# ==================== ПАТЧ №11: .gitignore для секретов и мусора ====================
# Проблемы:
#   1) "API ключ.txt" попал в staging — это секрет, в публичный GitHub нельзя.
#   2) chroma_db/ — 28 МБ бинарей, пересобирается build_embeddings.py.
#   3) tests/report_*.txt и tests/results_*.json — старые отчёты, мусор.
# Фикс: расширяем .gitignore, удаляем старые отчёты. Файл с ключом
# остаётся на диске, но git его игнорирует.

from pathlib import Path
import glob

ROOT = Path(__file__).resolve().parent.parent

GITIGNORE = """# Python
__pycache__/
*.py[cod]
*.egg-info/
.pytest_cache/
.mypy_cache/
htmlcov/
.coverage

# Бэкапы
*.bak
*.bak[0-9]
*.bak[0-9][0-9]

# Секреты — НИКОГДА не коммитить
.streamlit/secrets.toml
secrets.toml
*ключ*.txt
*secret*.txt
*key*.txt
*.env
.env

# Локальные данные
logs/
*.log
venv/
.venv/

# Тяжёлые бинарники / пересобираемое
chroma_db/
data/
legacy/
docs/screenshots/

# Старые отчёты тестов (не нужны в репо)
tests/report_*.txt
tests/results_*.json
"""

gi = ROOT / ".gitignore"
gi.write_text(GITIGNORE, encoding="utf-8")
print(f"[ok] .gitignore обновлён ({len(GITIGNORE)} символов)")

# ---------- Удаляем старые отчёты (не нужны) ----------
patterns = [
    "tests/report_*.txt",
    "tests/results_*.json",
]
deleted = 0
for pat in patterns:
    for f in glob.glob(str(ROOT / pat)):
        Path(f).unlink()
        deleted += 1
print(f"[ok] удалено старых отчётов: {deleted}")

# ---------- Проверка: что теперь попадёт в git ----------
print("\n[check] Файлы в корне:")
for p in sorted(ROOT.iterdir()):
    if p.is_file() and p.name != ".gitignore":
        print(f"  {p.name}")
print("\n[check] tests/:")
for p in sorted((ROOT / "tests").iterdir()):
    print(f"  {p.name}")

print("\nOK, патч №11 применён.")
print("\n⚠️  Файл 'API ключ.txt' остаётся на диске, но git его игнорирует.")
print("   Проверь сам — если там реальный ключ, лучше удали вручную.")