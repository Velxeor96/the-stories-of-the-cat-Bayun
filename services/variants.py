"""services/variants.py — гарантированные варианты действий в конце сцены."""
from __future__ import annotations

import re

_VARIANTS_HEADER_RE = re.compile(
    r"(Варианты действий|Что делаешь|Твой ход)[?:]?",
    re.IGNORECASE,
)
_INEVITABLE_TAIL = "Иное: опиши."

DEFAULT_VARIANTS = [
    "Осмотреться. Ты оцениваешь обстановку.",
    "Двигаться дальше. Ты делаешь следующий шаг.",
    "Ждать. Ты слушаешь и наблюдаешь.",
]


def ensure_action_variants(text: str) -> str:
    """Если в тексте нет блока вариантов — добавить его."""
    if not text or not text.strip():
        return text

    if _VARIANTS_HEADER_RE.search(text):
        return text

    lines = [
        "",
        "",
        "**Варианты действий:**",
        "",
    ]
    for v in DEFAULT_VARIANTS:
        lines.append(f"- {v}")
    lines.append(f"- {_INEVITABLE_TAIL}")
    return text.rstrip() + "\n".join(lines)
