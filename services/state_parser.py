# PATCH_16J
# services/state_parser.py — разбор блока [STATE] из нарратива Мастера.
from __future__ import annotations

import re


_BLOCK_RE = re.compile(
    r"\[STATE\](.*?)\[/STATE\]",
    re.DOTALL | re.IGNORECASE,
)


def parse_state(text):
    # Возвращает (clean_text, changes_dict).
    # clean_text — нарратив без блока [STATE] и без лишних пустых строк.
    # changes_dict — словарь {key: value}. При повторяющихся ключах
    # (напр. armour_unequip=arms дважды) значение становится списком.
    if not text:
        return text, {}

    changes = {}
    blocks = _BLOCK_RE.findall(text)
    for block in blocks:
        for line in block.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip()
            if not key:
                continue
            if key in changes:
                prev = changes[key]
                if isinstance(prev, list):
                    prev.append(value)
                else:
                    changes[key] = [prev, value]
            else:
                changes[key] = value

    clean = _BLOCK_RE.sub("", text)
    clean = re.sub(r"\n{3,}", "\n\n", clean).strip()
    return clean, changes
