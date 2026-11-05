import os
import zipfile
import json
from pathlib import Path

def _ensure_hf_cache() -> None:
    try:
        import sentence_transformers
    except ImportError:
        print('[bootstrap] sentence-transformers не установлен -> HF-кэш не нужен')
        return
    root = Path(__file__).resolve().parents[1]
    hub_root = Path.home() / ".cache" / "huggingface" / "hub"
    model_dir = hub_root / "models--intfloat--multilingual-e5-small"
    snap_dir = model_dir / "snapshots"

    if snap_dir.exists() and any(snap_dir.rglob("model.safetensors")):
        return

    manifest_path = root / "hf_cache_manifest.json"
    if not manifest_path.exists():
        print("[bootstrap] hf_cache_manifest.json не найден -> HF-кэш не распакуется")
        return

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        parts = manifest.get("parts", [])
        if not parts: return

        full_zip = root / "_hf_cache_assembled.zip"
        with open(full_zip, "wb") as out:
            for part in parts:
                pp = root / part
                if not pp.exists():
                    print(f"[bootstrap] Отсутствует часть {part} -> отказ")
                    return
                out.write(pp.read_bytes())

        model_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(full_zip, "r") as zf:
            zf.extractall(model_dir)

        try:
            full_zip.unlink()
        except Exception:
            pass
        print(f"[bootstrap] HF-кэш распакован: {model_dir}")
    except Exception as e:
        print(f"[bootstrap] HF cache error: {type(e).__name__}: {e}")

def _ensure_chroma_db() -> None:
    root = Path(__file__).resolve().parents[1]
    db_dir = root / "chroma_db"
    zip_path = root / "chroma_db.zip"
    
    if db_dir.exists() and any(db_dir.iterdir()):
        return
        
    if not zip_path.exists():
        print("[bootstrap] chroma_db/ нет, chroma_db.zip нет -> RAG отключён")
        return
        
    try:
        size_mb = zip_path.stat().st_size / (1024 * 1024)
        print(f"[bootstrap] chroma_db.zip найден ({size_mb:.1f} МБ), распаковываю...")
        db_dir.mkdir(exist_ok=True)
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(db_dir)
        n = sum(len(f) for _, _, f in os.walk(db_dir))
        print(f"[bootstrap] chroma_db/ распакован: {n} файлов")
    except Exception as e:
        print(f"[bootstrap] распаковка chroma_db.zip упала: {type(e).__name__}: {e}")

def init_project():
    _ensure_hf_cache()
    _ensure_chroma_db()
