"""services/text_validator.py — Пост-фильтр для ответов Мастера."""
from __future__ import annotations
import re

# Словарь жестких замен
_FIXES = {
    r"\bАхарак\b": "Сзарек",
    r"\bАбадон\b": "Абаддон",
    r"\bАзуриан\b": "Асуриан",
    r"\bварпоман\b": "псайкер",
    r"\bТёмные Механикум\b": "Тёмный Механикум",
}

def scrub(text: str) -> str:
    """Применяет жесткие замены к тексту мастера."""
    if not text:
        return text
    out = text
    for pattern, repl in _FIXES.items():
        out = re.sub(pattern, repl, out, flags=re.IGNORECASE)
    
    # Если ИИ начал выдумывать Новый Иерусалим — мягко гасим
    if "Новый Иерусалим" in out:
        out = out.replace("Новый Иерусалим", "улей")
        
    return out
