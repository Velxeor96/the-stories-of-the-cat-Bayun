"""Гарантирует наличие блока 'Варианты действий' в ответе Мастера.

Стратегия: пост-обработка текста. Если модель забыла блок (частая беда
flash-моделей в длинном промте) — Python дописывает безопасный fallback.

Позже заменим на реальные варианты, которые Analyst будет класть в JSON.
"""
from __future__ import annotations

import re

VARIANT_HEADER = "Варианты действий:"
FALLBACK_VARIANTS = [
    ("Осмотреться", "Ты оглядываешься по сторонам, оценивая обстановку."),
    ("Заговорить", "Ты обращаешься к тому, кто сейчас перед тобой."),
    ("Идти дальше", "Ты делаешь шаг вперёд, не задерживаясь."),
]


def has_variants(text: str) -> bool:
    """Есть ли в тексте блок 'Варианты действий' с 'Иное: опиши'."""
    if not text:
        return False
    low = text.lower()
    return "варианты действий" in low and "иное: опиши" in low


def build_fallback_block() -> str:
    """Собирает безопасный fallback-блок вариантов."""
    lines = [VARIANT_HEADER, ""]
    for i, (title, desc) in enumerate(FALLBACK_VARIANTS, start=1):
        lines.append(f"{i}. **{title}.** {desc}")
    lines.append("")
    lines.append("4. **Иное: опиши.**")
    return "\n".join(lines)


def ensure_action_variants(text: str) -> str:
    """Если в тексте нет блока вариантов — дописываем fallback.

    Возвращает текст с гарантированным блоком. Если варианты уже есть —
    возвращает текст без изменений.
    """
    if not text:
        return text
    if has_variants(text):
        return text
    return text.rstrip() + "\n\n" + build_fallback_block() + "\n"
