r"""
Тесты Analyst. Делают реальные запросы к LLM (~0,002 руб за прогон).

Запуск (из корня проекта):
    python tests\\test_analyst.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.analyst import Analyst, AnalystError  # noqa: E402
from core.config import Config  # noqa: E402


def check(label: str, condition: bool, info: str = "") -> bool:
    if condition:
        print(f"[ ok ] {label}")
        return True
    print(f"[FAIL] {label} {info}")
    return False


def main() -> None:
    ok = True

    print("=== Загрузка конфига ===")
    cfg = Config.load()
    print(cfg.summary())
    print()

    print("=== Инициализация Analyst ===")
    try:
        analyst = Analyst(cfg)
        print(f"Промт: {analyst.prompt_path}")
        print(f"Модель: {analyst.model.id}")
    except AnalystError as e:
        print(f"[ERR] {e}")
        sys.exit(1)
    print()

    tests = [
        ("Беру кинжал", "take", False, None),
        ("Осматриваю сундук", "observe", True, "Per"),
        ("Атакую орка мечом", "attack_melee", True, "WS"),
        ("Пытаюсь убедить инквизитора", "persuade", True, "Fel"),
        ("Иду к докам", "move", False, None),
    ]

    for phrase, exp_action, exp_roll, exp_skill in tests:
        print(f"\n--- «{phrase}» ---")
        try:
            r = analyst.parse(phrase)
            print(f"  → {r.to_dict()}")
            ok &= check(f"action = {exp_action}", r.action == exp_action, f"(получено: {r.action})")
            ok &= check(f"roll_needed = {exp_roll}", r.roll_needed == exp_roll)
            if exp_skill:
                ok &= check(f"skill = {exp_skill}", r.skill == exp_skill, f"(получено: {r.skill})")
        except AnalystError as e:
            print(f"[FAIL] Ошибка: {e}")
            ok = False

    print()
    if ok:
        print("ВСЕ ТЕСТЫ ПРОШЛИ.")
    else:
        print("ЕСТЬ ПАДЕНИЯ, см. выше.")
        sys.exit(1)


if __name__ == "__main__":
    main()
