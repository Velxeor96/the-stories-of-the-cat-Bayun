"""Фиктивные LLM-ответы для тестов без трат на API.

Принцип: LLMClient хранит call_fn в self.call_fn. Заменяем его
на функцию, которая отдаёт заготовленный OpenAI-совместимый ответ.
Никаких изменений в core/ — только monkey-patch в тестах.
"""
from __future__ import annotations

from typing import Any, Callable, Optional, Union


class _FakeMessage:
    def __init__(self, content: str):
        self.content = content


class _FakeChoice:
    def __init__(self, content: str):
        self.message = _FakeMessage(content)


class FakeResponse:
    """Минимальный мок ответа OpenAI-совместимого API."""
    def __init__(self, content: str):
        self.choices = [_FakeChoice(content)]


def make_fake_do_request(
    content_provider: Union[str, list, Callable[..., str]],
) -> Callable[..., FakeResponse]:
    """Собирает функцию, совместимую с _do_request.

    content_provider может быть:
      - строкой (всегда один и тот же ответ),
      - списком строк (выдаются по порядку; последний повторяется),
      - callable(**kwargs) -> str.
    """
    if isinstance(content_provider, str):
        def _call(**kwargs: Any) -> FakeResponse:
            return FakeResponse(content_provider)
        return _call

    if isinstance(content_provider, list):
        if not content_provider:
            raise ValueError("content_provider list пуст")
        state = {"i": 0}

        def _call(**kwargs: Any) -> FakeResponse:
            i = min(state["i"], len(content_provider) - 1)
            state["i"] += 1
            return FakeResponse(content_provider[i])
        return _call

    if callable(content_provider):
        def _call(**kwargs: Any) -> FakeResponse:
            return FakeResponse(content_provider(**kwargs))
        return _call

    raise TypeError(f"Неподдерживаемый тип: {type(content_provider).__name__}")


def patch_master(master: Any, content_provider: Any) -> Callable[..., Any]:
    """Подменяет Master._do_request на фейк. Возвращает оригинал."""
    original = master.llm.call_fn
    master.llm.call_fn = make_fake_do_request(content_provider)
    return original


def patch_analyst(analyst: Any, content_provider: Any) -> Callable[..., Any]:
    """Подменяет Analyst._do_request на фейк. Возвращает оригинал."""
    original = analyst.llm.call_fn
    analyst.llm.call_fn = make_fake_do_request(content_provider)
    return original


# ---------- Готовые сценарии ----------

FAKE_MASTER_SCENE = """Коридор «Крыла Кхейна» дышит ровным полумраком. Кость-призрак под ногами тёплая, живая.

Стражник у развилки провожает тебя взглядом, но молчит. Воздух сухой, с привкусом озона.

Что делаешь?"""

FAKE_MASTER_SCENE_WITH_VARIANTS = FAKE_MASTER_SCENE + """

Варианты действий:

1. **Осмотреться.** Ты оглядываешься по сторонам.
2. **Заговорить.** Ты обращаешься к стражнику.
3. **Идти дальше.** Ты идёшь по коридору.

4. **Иное: опиши.**"""

FAKE_ANALYST_OBSERVE = (
    '{"action": "observe", "target": null, "skill": "Per",'
    ' "roll_needed": true, "difficulty": "Ordinary"}'
)

FAKE_ANALYST_ATTACK = (
    '{"action": "attack_melee", "target": "орк", "skill": "WS",'
    ' "roll_needed": true, "difficulty": "Challenging"}'
)

FAKE_ANALYST_TALK = (
    '{"action": "talk", "target": "стражник", "skill": null,'
    ' "roll_needed": false, "difficulty": "Trivial"}'
)
