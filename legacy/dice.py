import random
import re


def roll_dice(expression: str, reason: str = "", difficulty: int = None) -> dict:
    """
    Бросает кубики по стандартной нотации.
    Если передан difficulty > 0 — определяет успех/провал.
    Если difficulty = 0 или None — бросок без порога (урон, генерация).
    """
    match = re.match(r"(\d+)d(\d+)([+-]\d+)?", expression.strip().lower())
    if not match:
        return {
            "error": f"Не удалось разобрать выражение: {expression}",
            "expression": expression,
            "reason": reason,
        }

    count = int(match.group(1))
    sides = int(match.group(2))
    modifier = int(match.group(3)) if match.group(3) else 0

    rolls = [random.randint(1, sides) for _ in range(count)]
    total = sum(rolls) + modifier

    result = {
        "expression": expression,
        "reason": reason,
        "rolls": rolls,
        "modifier": modifier,
        "total": total,
    }

    # Определяем успех/провал, если сложность > 0
    if difficulty is not None:
        try:
            difficulty = int(difficulty)
            if difficulty <= 0:
                # 0 или меньше — маркер "без проверки" (урон, генерация)
                return result

            result["difficulty"] = difficulty
            if total <= difficulty:
                result["success"] = True
                result["margin"] = (difficulty - total) // 10
            else:
                result["success"] = False
                result["margin"] = (total - difficulty) // 10
        except (ValueError, TypeError):
            pass

    return result


def format_roll_result(result: dict) -> str:
    if "error" in result:
        return f"Ошибка броска: {result['error']}"

    rolls_str = ", ".join(str(r) for r in result["rolls"])
    modifier_str = ""
    if result["modifier"] != 0:
        modifier_str = f" {result['modifier']:+d}"

    reason = f" ({result['reason']})" if result["reason"] else ""

    base = (
        f"Бросок {result['expression']}{reason}: "
        f"выпало [{rolls_str}]{modifier_str} = **{result['total']}**"
    )

    if "success" in result:
        if result["success"]:
            base += (
                f" — ✅ УСПЕХ (сложность {result['difficulty']}, "
                f"степеней успеха: {result['margin']})"
            )
        else:
            base += (
                f" — ❌ ПРОВАЛ (сложность {result['difficulty']}, "
                f"степеней провала: {result['margin']})"
            )

    return base


# ===== Тестирование =====
if __name__ == "__main__":
    print("Тестируем броски кубиков:\n")

    tests = [
        ("1d100", "проверка Дальнего боя", 45),
        ("1d100", "проверка Дальнего боя", 45),
        ("1d10+5", "урон болтера", 0),
        ("1d10+3", "урон сюрикен-пистолета", 0),
        ("2d10+20", "генерация характеристики", 0),
    ]

    for expr, reason, diff in tests:
        result = roll_dice(expr, reason, diff)
        print(format_roll_result(result))