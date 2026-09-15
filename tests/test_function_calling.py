import sys
import os

# Добавляем родительскую папку (my_game) в sys.path,
# чтобы можно было импортировать dice.py
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


import json
from gigachat import GigaChat
from gigachat.models import (
    ChatCompletionRequest,
    ChatMessage,
    ChatContentPart,
    ChatFunctionSpecification,
    ChatFunctionsTool,
    ChatTool,
)
from gigachat.models.chat_completions import ChatFunctionResult

# ===== НАСТРОЙКИ =====
AUTH_KEY = "MDFhMDk2NGMtZGQ0Yi03NGJiLTkzNWEtODgzMWEwNjZjZDYzOjBkNDViZDZmLTYxYzQtNGYyNC1hYzFlLTczZGY5OWI5MDZiMw=="


def extract_function_call(message: ChatMessage):
    """Извлекает function_call из ответа GigaChat."""
    if message.function_call is not None:
        return message.function_call
    for part in message.content or []:
        if part.function_call is not None:
            return part.function_call
    return None


def get_arguments(function_call) -> dict:
    """Возвращает аргументы функции как словарь (поддерживает dict, str, partial_arguments)."""
    args = getattr(function_call, "arguments", None)
    if args is None:
        args = getattr(function_call, "partial_arguments", None)
    if isinstance(args, str):
        args = json.loads(args)
    return args or {}


def main():
    print("=" * 60)
    print("ТЕСТ FUNCTION CALLING (финальная версия)")
    print("=" * 60)

    giga = GigaChat(
        credentials=AUTH_KEY,
        scope="GIGACHAT_API_PERS",
        verify_ssl_certs=False,
        model="GigaChat-2-Pro",
    )

    # ===== ОПИСАНИЕ ФУНКЦИИ =====
    roll_dice_function = ChatFunctionSpecification(
        name="roll_dice",
        description=(
            "Бросает кубики по стандартной нотации. "
            "Используй эту функцию КАЖДЫЙ РАЗ, когда нужно проверить навык, "
            "определить урон, сгенерировать характеристику или сделать любой "
            "другой бросок. НИКОГДА не выдумывай результат броска — всегда "
            "вызывай эту функцию."
        ),
        parameters={
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "Формат броска: '1d100', '2d10', '1d10+5'.",
                },
                "reason": {
                    "type": "string",
                    "description": "Что проверяется. Например: 'проверка Дальнего боя, сложность 45'.",
                },
            },
            "required": ["expression", "reason"],
        },
    )

    # ===== ЧИТАЕМ ПРОМТ ИЗ master.txt =====
    with open("../prompts/master.txt", "r", encoding="utf-8") as f:
        system_prompt = f.read()

    # ===== ИСТОРИЯ =====
    messages = [
        ChatMessage(role="system", content=[ChatContentPart(text=system_prompt)]),
    ]

    user_request = (
        "Я стреляю из сюрикен-пистолета по орку. Проверь мой Дальний бой "
        "со сложностью 45."
    )
    messages.append(ChatMessage(
        role="user",
        content=[ChatContentPart(text=user_request)],
    ))

    print(f"\n[Игрок]: {user_request}\n")
    print("Отправляю запрос в GigaChat...\n")

    # ===== ПЕРВЫЙ ЗАПРОС =====
    request = ChatCompletionRequest(
        messages=messages,
        tools=[ChatTool(functions=ChatFunctionsTool(specifications=[roll_dice_function]))],
    )

    response = giga.chat.create(request)
    assistant_message = response.messages[0]

    function_call = extract_function_call(assistant_message)

    if function_call is None:
        print("⚠️ GigaChat НЕ вызвал функцию. Вот его ответ:")
        print(assistant_message.content)
        return

    print("✅ GigaChat вызвал функцию!")
    print(f"   Имя: {function_call.name}")
    print(f"   Аргументы: {get_arguments(function_call)}\n")

    # ===== АРГУМЕНТЫ =====
    args = get_arguments(function_call)
    expression = args.get("expression")
    reason = args.get("reason", "")

    # ===== БРОСОК =====
    from dice import roll_dice, format_roll_result
    result = roll_dice(expression, reason)
    formatted = format_roll_result(result)

    print(f"🎲 Результат: {formatted}\n")

    # ===== ДОБАВЛЯЕМ В ИСТОРИЮ =====
    # 1. Assistant с вызовом функции (берём как есть из ответа)
    messages.append(assistant_message)

    # 2. Результат функции в формате ChatContentPart.function_result
    function_result = ChatFunctionResult(
        name="roll_dice",
        result=json.dumps(result, ensure_ascii=False),
    )
    messages.append(ChatMessage(
        role="function",
        content=[ChatContentPart(function_result=function_result)],
    ))

    print("Отправляю результат обратно в GigaChat...\n")

    # ===== ВТОРОЙ ЗАПРОС =====
    second_request = ChatCompletionRequest(
        messages=messages,
        tools=[ChatTool(functions=ChatFunctionsTool(specifications=[roll_dice_function]))],
    )
    second_response = giga.chat.create(second_request)
    final_message = second_response.messages[0]

    print("=" * 60)
    print("[Мастер]:")
    print("=" * 60)
    if final_message.content:
        for part in final_message.content:
            if part.text:
                print(part.text)
    print("=" * 60)


if __name__ == "__main__":
    main()