# scripts/patch.py — PATCH_39: git preflight + подготовка к push
from __future__ import annotations
import os, sys
from pathlib import Path

TAG = "PATCH_39"
ROOT = Path(__file__).resolve().parent.parent

r = {"ok": [], "warn": [], "errors": []}


# 1. Проверяем .gitignore
gitignore = ROOT / ".gitignore"
required = [
    ".env",
    ".streamlit/secrets.toml",
    "gigachat_key.txt",
    "__pycache__/",
    "*.pyc",
    "*.bak*",
    "data/users/*/",
    "data/users/*.json",
    "data/users/*/autosave/",
    "data/_index.json",
    "chroma_db/",
    ".DS_Store",
    "Thumbs.db",
]

current = ""
if gitignore.exists():
    current = gitignore.read_text(encoding="utf-8")
else:
    r["warn"].append(".gitignore отсутствует — создаю")

missing = [p for p in required if p not in current]

if missing:
    add_block = "\n# PATCH_39: git preflight\n" + "\n".join(missing) + "\n"
    with open(gitignore, "a", encoding="utf-8") as f:
        f.write(add_block)
    r["ok"].append(".gitignore дополнен: " + str(len(missing)) + " паттернов")
else:
    r["ok"].append(".gitignore в порядке")

# 2. Проверяем крупные/опасные файлы в корне
danger = []
for name in ("gigachat_key.txt", ".env", "secrets.toml"):
    if (ROOT / name).exists():
        danger.append(name)
if (ROOT / ".streamlit" / "secrets.toml").exists():
    danger.append(".streamlit/secrets.toml")

if danger:
    r["warn"].append("Есть файлы, которые НЕ должны попасть в репо: "
                     + ", ".join(danger))
else:
    r["ok"].append("Секретов в корне нет")

# 3. Размер chroma_db
cdb = ROOT / "chroma_db"
if cdb.exists():
    total = 0
    for p in cdb.rglob("*"):
        if p.is_file():
            try:
                total += p.stat().st_size
            except Exception:
                pass
    mb = total // (1024 * 1024)
    r["ok"].append("chroma_db: " + str(mb) + " МБ "
                   + ("(в .gitignore, не пушится)" if "chroma_db/" in current
                      or "chroma_db/" in required else "(!) не игнорируется"))

# 4. data/users
udir = ROOT / "data" / "users"
if udir.exists():
    users = [d for d in udir.iterdir() if d.is_dir()]
    r["ok"].append("data/users: " + str(len(users)) + " пользователей "
                   + "(игнорируется)")

# 5. VERSION
vp = ROOT / "VERSION"
if vp.exists():
    r["ok"].append("VERSION: " + vp.read_text(encoding="utf-8").strip())

# 6. Сколько *.bak_pre_* накопилось
baks = list(ROOT.rglob("*.bak_pre_*"))
r["ok"].append("*.bak_pre_* файлов: " + str(len(baks)) + " (в .gitignore)")

print("=== " + TAG + " ===")
for x in r["ok"]:
    print("  [OK]   " + x)
for x in r["warn"]:
    print("  [WARN] " + x)
for x in r["errors"]:
    print("  [ERR]  " + x)
print("READY" if not r["errors"] else "NOT READY")