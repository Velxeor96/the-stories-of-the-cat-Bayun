# scripts/patch.py — PATCH_72: автораспаковка HF-кэша из hf_cache_part*.zip
from __future__ import annotations
import ast, shutil, sys
from pathlib import Path

TAG = "PATCH_72"
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

p = ROOT / "app.py"
text = p.read_text(encoding="utf-8")

MARKER = "# PATCH_72: автораспаковка HF-кэша"

BOOTSTRAP = '''
# PATCH_72: автораспаковка HF-кэша
def _ensure_hf_cache() -> None:
    import os
    import zipfile
    import json
    from pathlib import Path
    root = Path(__file__).resolve().parent
    hub_root = Path.home() / ".cache" / "huggingface" / "hub"
    model_dir = hub_root / "models--intfloat--multilingual-e5-small"
    snap_dir = model_dir / "snapshots"

    # Проверяем — есть ли уже модель
    if snap_dir.exists() and any(snap_dir.rglob("model.safetensors")):
        return

    manifest_path = root / "hf_cache_manifest.json"
    if not manifest_path.exists():
        print("[app] hf_cache_manifest.json не найден -> HF-кэш не распакуется")
        return

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        parts = manifest.get("parts", [])
        if not parts:
            return

        # Склеиваем части в один zip
        full_zip = root / "_hf_cache_assembled.zip"
        with open(full_zip, "wb") as out:
            for part in parts:
                pp = root / part
                if not pp.exists():
                    print(f"[app] Отсутствует часть {part} -> отказ")
                    return
                out.write(pp.read_bytes())

        # Распаковываем содержимое модели прямо в её папку
        model_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(full_zip, "r") as zf:
            zf.extractall(model_dir)

        # Удаляем временный zip
        try:
            full_zip.unlink()
        except Exception:
            pass

        print(f"[app] HF-кэш распакован: {model_dir}")
    except Exception as e:
        print(f"[app] HF cache error: {type(e).__name__}: {e}")


_ensure_hf_cache()
# /PATCH_72

'''

if MARKER in text:
    r["modified"].append("app.py — HF-кэш уже прописан")
else:
    # Вставляем ПЕРЕД "# PATCH_66: offline-режим HuggingFace"
    ANCHOR = "# PATCH_66: offline-режим HuggingFace"
    if ANCHOR in text:
        text = text.replace(ANCHOR, BOOTSTRAP + ANCHOR, 1)
        try:
            ast.parse(text)
        except SyntaxError as e:
            r["errors"].append("app.py syntax: " + str(e))
        else:
            _bk(p)
            p.write_text(text, encoding="utf-8")
            r["modified"].append("app.py — +автораспаковка HF-кэша")
    else:
        r["errors"].append("app.py: якорь '# PATCH_66' не найден")

print("=== PATCH " + TAG + " ===")
for m in r["modified"]:
    print("  [MODIFIED] " + m)
for e in r["errors"]:
    print("  [ERROR] " + e)
print("DONE" if not r["errors"] else "DONE (with errors)")