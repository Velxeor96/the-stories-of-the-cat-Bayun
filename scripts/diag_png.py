from pathlib import Path

SIG = b"\x89PNG\r\n\x1a\n"
d = Path("static/sigils")
print("Папка:", d.resolve())
print("=" * 72)
for f in sorted(d.glob("*.png")):
    data = f.read_bytes()
    ok = data[:8] == SIG
    tag = "OK" if ok else "NOT-PNG (" + data[:8].hex() + ")"
    print(f"{f.name:32s} {len(data):>8d}   {tag}")
print("=" * 72)
