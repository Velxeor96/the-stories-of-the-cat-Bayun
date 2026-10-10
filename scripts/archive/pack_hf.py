# scripts/pack_hf.py — режет hf_cache_full.zip на части по ~70 МБ
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "hf_cache_full.zip"
CHUNK_SIZE = 70 * 1024 * 1024  # 70 МБ

if not SRC.exists():
    print("[ERROR] hf_cache_full.zip не найден:", SRC)
    raise SystemExit(1)

data = SRC.read_bytes()
total = len(data)
n_parts = (total + CHUNK_SIZE - 1) // CHUNK_SIZE
print(f"[pack_hf] Размер: {total / 1024 / 1024:.1f} МБ, частей: {n_parts}")

parts = []
for i in range(n_parts):
    s = i * CHUNK_SIZE
    e = min(s + CHUNK_SIZE, total)
    chunk = data[s:e]
    name = f"hf_cache_part{i+1}.zip"
    out = ROOT / name
    out.write_bytes(chunk)
    parts.append(name)
    print(f"  [OK] {name}: {len(chunk) / 1024 / 1024:.1f} МБ")

manifest = {
    "total_size": total,
    "chunk_size": CHUNK_SIZE,
    "parts": parts,
}
(ROOT / "hf_cache_manifest.json").write_text(
    json.dumps(manifest, indent=2), encoding="utf-8")
print("[pack_hf] Манифест: hf_cache_manifest.json")
print("DONE")