# PATCH_38
"""services/master.py — Мастер с жёстким RACE LOCK."""
from __future__ import annotations
from pathlib import Path
from typing import Any, Optional

from core.config import Config
from core.llm_client import LLMClient
from core.llm_factory import make_client

ROOT_DIR = Path(__file__).resolve().parents[1]


class MasterError(Exception):
    pass


def _race_rule_for(faction_name: str) -> str:
    f = (faction_name or "").strip().lower()
    if "эльдар" in f or "eldar" in f:
        return ("ВАЖНО: игрок — АЭЛЬДАРИ (ЭЛЬДАР). НИКОГДА не называй его "
                "«моно-кеи», «человек», «гуманид». Если NPC-человек — он "
                "НЕ может оскорблять игрока чужими эльдарскими словами.")
    if "друкх" in f or "drukhari" in f:
        return "ВАЖНО: игрок — ДРУХКАРИ (Тёмный эльдар)."
    if "орк" in f or "ork" in f:
        return ("ВАЖНО: игрок — ОРК. Не называй его «человек», «гуманид». "
                "Он сам знает ВАААГХ.")
    if "тау" in f or "tau" in f:
        return "ВАЖНО: игрок — ТАУ. Люди для него — «гве'ла»."
    if "некрон" in f or "necron" in f:
        return "ВАЖНО: игрок — НЕКРОН. Древний. Машина. Без души."
    if "тиранид" in f or "tyranid" in f:
        return "ВАЖНО: игрок — биоморф ТИРАНИД. Речь через генокрада."
    if "генокрад" in f or "genestealer" in f:
        return "ВАЖНО: игрок — ГЕНОКРАД (гибрид Генокульта)."
    if "хаос" in f or "chaos" in f:
        return "ВАЖНО: игрок — последователь ХАОСА, а не обычный человек."
    if "империум" in f or "imperium" in f:
        return "Игрок — человек Империума."
    return "Игрок — НЕ человек по умолчанию. Раса = фракция из блока ПЕРСОНАЖ."


class Master:
    def __init__(self, config: Config, *, role: str = "master",
                 core_prompt: Optional[Path] = None,
                 lore_prompt: Optional[Path] = None):
        self.config = config
        self.role = role
        cp = core_prompt or (ROOT_DIR / "prompts" / "master_core.txt")
        lp = lore_prompt or (ROOT_DIR / "prompts" / "lore_reference.txt")
        vp = ROOT_DIR / "prompts" / "voice_lines.txt"
        rp = ROOT_DIR / "prompts" / "race_lock.txt"

        ct = Path(cp).read_text(encoding="utf-8") if Path(cp).exists() else ""
        lt = Path(lp).read_text(encoding="utf-8") if Path(lp).exists() else ""
        vt = Path(vp).read_text(encoding="utf-8") if Path(vp).exists() else ""
        rt = Path(rp).read_text(encoding="utf-8") if Path(rp).exists() else ""

        # RACE_LOCK — в самом начале системного промпта
        self.system_prompt = (
            rt + "\n\n" + ct
            + "\n\n=== ТЕРМИНОЛОГИЯ ===\n\n" + lt
            + "\n\n=== ГОЛОСА ФРАКЦИЙ ===\n\n" + vt
        )

        self.model = config.role_model(role)
        self.provider = config.provider(self.model.provider)
        self.api_key = config.provider_key(self.model.provider)
        self.base_url = self.provider.base_url
        retries = config.retries()
        self.llm = LLMClient(
            self._do_request,
            max_retries=retries.get("max_retries", 3),
            base_delay=retries.get("base_delay", 1.0),
            max_delay=retries.get("max_delay", 30.0),
        )

    def _get_max_tokens(self) -> int:
        try:
            import streamlit as _st
            lg = _st.session_state.get("user_login")
            if lg:
                from services.settings_game import max_tokens_for
                return max_tokens_for(lg)
        except Exception:
            pass
        return 700

    def narrate(self, state, command, *, roll=None, history=None,
                extra_context=""):
        msg = self._build_message(state=state, command=command, roll=roll,
                                  history=history or [],
                                  extra_context=extra_context)
        try:
            r = self.llm.call(
                system_prompt=self.system_prompt, user_message=msg,
                model=self.model.id, temperature=0.85,
                max_tokens=self._get_max_tokens())
            return self._extract_text(r)
        except Exception as e:
            print("[master] fallback: " + type(e).__name__ + ": " + str(e))
            return "[fallback-мастер] Попробуй переформулировать ход."

    @staticmethod
    def _build_message(*, state, command, roll, history, extra_context):
        parts = []

        # === САМОЕ ПЕРВОЕ: жёсткий race-lock ===
        try:
            if isinstance(state, dict):
                fname = str(state.get("faction") or "")
                sub = str(state.get("subfaction") or "")
                cwn = str(state.get("home_world_name") or "")
                crn = str(state.get("career_name") or "")
                lock = ["=== RACE LOCK (НАРУШЕНИЕ = ПРОВАЛ) ===",
                        _race_rule_for(fname)]
                if fname:
                    lock.append("Фракция игрока: " + fname
                                + (" / " + sub if sub else "") + ".")
                if cwn:
                    lock.append("Родной мир: " + cwn + ".")
                if crn:
                    lock.append("Карьера: " + crn + ".")
                lock.append("Не вводи реалии других фракций без причины.")
                lock.append("Не называй игрока чужой расой.")
                parts.append("\n".join(lock))
        except Exception as _e:
            print("[master] race-lock fail: " + type(_e).__name__)

        if isinstance(state, dict):
            sp = []
            for key, label in (("name", "Имя"), ("gender", "Пол"),
                               ("age", "Возраст"), ("appearance", "Внешность"),
                               ("faction", "Фракция"),
                               ("subfaction", "Субфракция"),
                               ("home_world_name", "Родной мир"),
                               ("career_name", "Карьера"),
                               ("user_background", "Предыстория")):
                v = state.get(key)
                if v:
                    sp.append(label + ": " + str(v))
            w = state.get("wounds") or {}
            if w:
                sp.append("Раны: " + str(w.get("current", 0))
                          + "/" + str(w.get("max", 0)))
            chars = state.get("characteristics") or {}
            if chars:
                sp.append("Характеристики: "
                          + ", ".join(str(k) + "=" + str(v)
                                      for k, v in chars.items()))
            if sp:
                parts.append("=== ПЕРСОНАЖ ===\n" + "\n".join(sp))

        try:
            from services.effects import effects_summary
            es = effects_summary(state)
            if es and es != "—":
                parts.append("=== ЭФФЕКТЫ ===\n" + es)
        except Exception:
            pass

        try:
            from services.ship import ship_summary
            ss = ship_summary(state)
            if ss:
                parts.append("=== КОРАБЛЬ ===\n" + ss)
        except Exception:
            pass

        try:
            from services.environment import env_summary
            es = env_summary(state)
            if es:
                parts.append("=== СРЕДА ===\n" + es)
        except Exception:
            pass

        try:
            from services.notes import render_notes_for_master
            nb = render_notes_for_master(state)
            if nb:
                parts.append(nb)
        except Exception:
            pass

        try:
            cs = __import__("streamlit").session_state.get("_combat_state")
            if cs and getattr(cs, "active", False):
                from services.combat import state_to_master_text
                parts.append(state_to_master_text(cs))
        except Exception:
            pass

        if history:
            # PATCH_67: history может быть dict {"role": "player"|"master", "text": "..."}
            # или dataclass TurnResult (в старом формате). Поддерживаем оба.
            import re as _re
            hl = ["=== ПОСЛЕДНИЕ ХОДЫ (продолжай сцену, не начинай заново) ==="]
            recent = history[-12:]  # ~6 пар ход-ответ
            for t in recent:
                if isinstance(t, dict):
                    role = str(t.get("role", "")).lower()
                    txt = str(t.get("text", ""))
                    if role == "player":
                        hl.append("> Игрок: " + txt[:600])
                    elif role == "master":
                        clean = _re.sub(r"<!--ROLLCARD:.*?-->", "",
                                        txt, flags=_re.DOTALL)
                        clean = _re.sub(r"\[STATE\].*?\[/STATE\]", "",
                                        clean, flags=_re.DOTALL)
                        hl.append("Мастер: " + clean.strip()[:1200])
                else:
                    # fallback: TurnResult-объект
                    if hasattr(t, "player_input") and t.player_input:
                        hl.append("> Игрок: " + str(t.player_input)[:600])
                    if hasattr(t, "narrative") and t.narrative:
                        hl.append("Мастер: " + str(t.narrative)[:1200])
            if len(hl) > 1:
                hl.append("=== СЮЖЕТ: ПРОДОЛЖАЙ ИСТОРИЮ С ЭТОГО МОМЕНТА, "
                          "НЕ ПЕРЕСКАЗЫВАЙ ВСТУПЛЕНИЕ. ===")
                parts.append("\n".join(hl))

        action = getattr(command, "action", "?")
        raw = getattr(command, "raw", "")
        parts.append("=== ДЕЙСТВИЕ ===\nТип: " + str(action)
                     + "\nФраза: " + repr(raw))

        if roll is not None:
            res = "УСПЕХ" if roll.success else "ПРОВАЛ"
            parts.append("=== БРОСОК ===\n" + res
                         + "\n" + str(roll.roll) + " vs " + str(roll.target))
        else:
            parts.append("=== БРОСОК ===\nНе требовался.")

        parts.append(extra_context if extra_context
                     else "=== СПРАВКА ===\nНет данных.")

        parts.append("=== ЗАДАЧА ===\nОпиши сцену, 2–4 варианта действий. "
                     "NPC говорят голосами своих фракций.")
        parts.append("=== НАПОМИНАНИЕ ===\nИгрок — НЕ человек по умолчанию. "
                     "Его раса — из блока ПЕРСОНАЖ. НЕ называй его чужой расой.")
        return "\n\n".join(parts)

    def _do_request(self, *, system_prompt, user_message, model,
                    temperature, max_tokens):
        client = make_client(provider_key=self.model.provider,
                             api_key=self.api_key, base_url=self.base_url)
        return client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=temperature, max_tokens=max_tokens,
        )

    @staticmethod
    def _extract_text(response):
        try:
            return response.choices[0].message.content or ""
        except (AttributeError, IndexError) as e:
            raise MasterError("формат: " + repr(response)) from e
