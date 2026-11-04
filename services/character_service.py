"""services/character_service.py — единый источник правды для статов.

Правила:
  - home_world и career бонусы берутся по faction_id (как в build_character).
  - бонусы архетипа берутся по _effective_id (= subfaction_id or faction_id),
    как в build_character через _kit_key. Для alien-фракций архетип берётся
    из services.<faction_id> — DLC подхватится автоматически.
"""
from __future__ import annotations

import importlib

from services.character_creation import build_character
from services.faction_starting import get_home_world_bonuses, get_career_bonuses
from services.fallbacks import home_world_display_name, career_display_name

# Имперские субфракции с архетипами. При добавлении новой субфракции —
# допишите сюда строку.
_IMPERIAL_ARCH_SERVICES = {
    "imperial_guard": "services.imperial_guard",
    "mechanicus": "services.mechanicus",
    "inquisition": "services.inquisition",
    "sororitas": "services.sororitas",
    "space_marine": "services.space_marines",
    "arbites": "services.arbites",
}


def _get_archetype_bonus(effective_id, career_id):
    """Возвращает bonus_characteristics архетипа.

    Порядок поиска:
      1) имперская субфракция из _IMPERIAL_ARCH_SERVICES;
      2) alien-модуль services.<effective_id> с методом get_archetype.
    """
    if effective_id in _IMPERIAL_ARCH_SERVICES:
        try:
            mod = importlib.import_module(_IMPERIAL_ARCH_SERVICES[effective_id])
            arch = mod.get_archetype(career_id or "")
            if arch:
                return arch.get("bonus_characteristics", {}) or {}
        except Exception:
            pass
        return {}

    try:
        mod = importlib.import_module("services." + str(effective_id))
    except Exception:
        return {}
    if not hasattr(mod, "get_archetype"):
        return {}
    try:
        arch = mod.get_archetype(career_id or "")
    except Exception:
        return {}
    if not arch:
        return {}
    return arch.get("bonus_characteristics", {}) or {}


def calculate_preview(faction_id, effective_id, home_world_id, career_id, base_stats):
    """Финальные статы так же, как их посчитает build_character."""
    hw_name = home_world_display_name(faction_id, home_world_id)
    cr_name = career_display_name(faction_id, career_id)

    hw_b = get_home_world_bonuses(faction_id, hw_name)
    cr_b = get_career_bonuses(faction_id, cr_name)
    arch_b = _get_archetype_bonus(effective_id, career_id)

    result = dict(base_stats)
    for k, v in (hw_b["bonus"] or {}).items():
        if k in result:
            result[k] += int(v)
    for k, v in (hw_b["penalty"] or {}).items():
        if k in result:
            result[k] -= int(v)
    for k, v in (cr_b["bonus"] or {}).items():
        if k in result:
            result[k] += int(v)
    for k, v in (cr_b["penalty"] or {}).items():
        if k in result:
            result[k] -= int(v)
    for k, v in arch_b.items():
        if k in result:
            result[k] += int(v)
    return result


def validate_and_build(name, gender, age, appearance, user_background,
                       faction_id, subfaction_id, home_world_id, career_id,
                       stats_dict):
    total_spent = sum(stats_dict.values()) - (25 * 9)
    if total_spent > 200:
        raise ValueError("Превышен лимит очков (200).")
    if max(stats_dict.values()) > 60:
        raise ValueError("Характеристика не может быть больше 60.")

    return build_character(
        name=name, gender=gender, age=age, appearance=appearance,
        user_background=user_background, faction_id=faction_id,
        subfaction_id=subfaction_id, home_world_id=home_world_id,
        career_id=career_id, characteristics=stats_dict,
    )
