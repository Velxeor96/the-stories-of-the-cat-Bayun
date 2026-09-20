"""core/version.py — читает VERSION и отдаёт строку версии."""
from pathlib import Path

_VERSION_FILE = Path(__file__).resolve().parents[1] / "VERSION"


def get_version() -> str:
    """Вернуть строку версии из файла VERSION (например, 'Alfa 2.0')."""
    if not _VERSION_FILE.exists():
        return "unknown"
    try:
        return _VERSION_FILE.read_text(encoding="utf-8").strip() or "unknown"
    except Exception:
        return "unknown"
