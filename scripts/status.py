"""scripts/status.py — что в проекте работает, что нет."""
import os, sys, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def h1(s):
    print()
    print("=" * 60)
    print(s)
    print("=" * 60)


def h2(s):
    print()
    print(f"--- {s} ---")


# 1. Config
h1("1. CONFIG")
try:
    from core.config import Config
    cfg = Config.load()
    print("Провайдеры:")
    for k, p in cfg.data["providers"].items():
        has_key = "ЕСТЬ" if cfg.secrets.get(p["api_key_env"]) else "НЕТ"
        print(f"  {k:12s}  key_env={p['api_key_env']:22s}  ключ: {has_key}")
    print("Модели:")
    for k, m in cfg.data["models"].items():
        print(f"  {k:18s}  id={m['id']:35s}  provider={m['provider']}")
    print("Роли:")
    for role, mk in cfg.data["roles"].items():
        m = cfg.data["models"][mk]
        print(f"  {role:10s} -> {mk:18s} ({m['provider']}, {m['id']})")
except Exception as e:
    print(f"ОШИБКА: {type(e).__name__}: {e}")


# 2. Secrets
h2("Ключи в secrets.toml")
try:
    p = ROOT / ".streamlit" / "secrets.toml"
    if p.exists():
        import tomllib
        with p.open("rb") as f:
            data = tomllib.load(f)
        for k in data:
            print(f"  {k}")
    else:
        print("  файла нет")
except Exception as e:
    print(f"  ОШИБКА: {e}")


# 3. Импорт модулей core
h1("3. ИМПОРТ CORE-МОДУЛЕЙ")
mods = sorted([p.stem for p in (ROOT / "core").glob("*.py") if p.stem != "__init__"])
for name in mods:
    try:
        __import__(f"core.{name}")
        print(f"  OK    core.{name}")
    except Exception as e:
        print(f"  FAIL  core.{name}: {type(e).__name__}: {e}")


# 4. GigaChat smoke test
h1("4. GIGACHAT SMOKE TEST")
try:
    import tomllib
    from core.llm_factory import make_client
    with (ROOT / ".streamlit" / "secrets.toml").open("rb") as f:
        s = tomllib.load(f)
    key = s.get("GIGACHAT_API_KEY")
    if not key:
        print("  нет GIGACHAT_API_KEY — пропуск")
    else:
        c = make_client("gigachat", key, "https://gigachat.devices.sberbank.ru/api/v1")
        r = c.chat.completions.create(
            model="GigaChat-2-Pro",
            messages=[{"role": "user", "content": "Скажи одно слово: тест"}],
            temperature=0.0, max_tokens=10,
        )
        print(f"  OK  ответ: {r.choices[0].message.content!r}")
except Exception as e:
    print(f"  FAIL: {type(e).__name__}: {e}")


# 5. Pytest
h1("5. PYTEST")
try:
    r = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-q", "--no-header"],
        cwd=str(ROOT), capture_output=True, text=True, timeout=120,
    )
    tail = r.stdout.strip().splitlines()[-5:]
    for line in tail:
        print(f"  {line}")
except Exception as e:
    print(f"  ОШИБКА: {e}")


# 6. Logs
h1("6. LOGS")
p = ROOT / "logs" / "errors.log"
if p.exists():
    data = p.read_text(encoding="utf-8", errors="replace")
    print(f"  размер: {len(data)} символов")
    print("  последние 1500 символов:")
    print(data[-1500:])
else:
    print("  logs/errors.log отсутствует")
    print("  → значит fallback ещё ни разу не срабатывал после последнего патча")


h1("ГОТОВО")
