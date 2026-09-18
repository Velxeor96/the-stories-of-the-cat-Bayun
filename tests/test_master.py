r"""
Тесты Master. Делают реальные запросы к LLM.

Запуск (из корня проекта):
    python tests\test_master.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.analyst import ParsedCommand  # noqa: E402
from core.config import Config  # noqa: E402
from core.master import Master, MasterError, Turn  # noqa: E402
from core.roll_engine import check  # noqa: E402
from core.state import CharacterState  # noqa: E402


def main() -> None:
    ok = True
    root = Path(__file__).resolve().parents[1]
    char_path = root / "characters" / "Костопевец.json"
    if not char_path.exists():
        print(f"[ERR] Нет файла персонажа: {char_path}")
        sys.exit(1)

    print("=== Загрузка конфига ===")
    cfg = Config.load()
    print(f"Модель Мастера: {cfg.role_model('master').id}")
    print()

    print("=== Загрузка персонажа ===")
    state = CharacterState.load(char_path)
    print(f"Персонаж: {state.data.get('name')}, раны {state.wounds}")
    print()

    print("=== Инициализация Master ===")
    try:
        master = Master(cfg)
        print(f"Ядро промта: {master.core_prompt_path}")
        print(f"Лор-справка: {master.lore_prompt_path}")
        print(f"Размер system_prompt: {len(master.system_prompt)} символов")
    except MasterError as e:
        print(f"[ERR] {e}")
        sys.exit(1)
    print()

    # --- Тест 1: ход без броска (игрок идёт) ---
    print("--- Тест 1: ход без броска ---")
    cmd = ParsedCommand(
        action="move",
        target="доки",
        skill=None,
        roll_needed=False,
        difficulty="Ordinary",
        raw="Иду к докам",
    )
    try:
        text = master.narrate(state, cmd)
        print(text)
        print()
        print(f"Длина ответа: {len(text)} символов")
        ok &= len(text) > 100
        # Проверка: нет служебных маркеров
        for bad in ["[STATE]", "wounds=", "🎲", "key=value"]:
            if bad in text:
                print(f"[FAIL] В тексте найден служебный маркер: {bad}")
                ok = False
        print("[ ok ] нет служебных маркеров")
    except MasterError as e:
        print(f"[FAIL] {e}")
        ok = False
    print()

    # --- Тест 2: ход с успешным броском ---
    print("--- Тест 2: ход с броском (успех) ---")
    cmd = ParsedCommand(
        action="observe",
        target="сундук",
        skill="Per",
        roll_needed=True,
        difficulty="Ordinary",
        raw="Осматриваю сундук",
    )
    roll = check(45, reason="Внимание")  # 45 = Per Костопевца
    print(f"Бросок: {roll.format_short()}")
    print()
    try:
        text = master.narrate(state, cmd, roll=roll)
        print(text)
        print()
        ok &= len(text) > 100
        for bad in ["[STATE]", "wounds=", "🎲"]:
            if bad in text:
                print(f"[FAIL] В тексте найден служебный маркер: {bad}")
                ok = False
        print("[ ok ] нет служебных маркеров")
    except MasterError as e:
        print(f"[FAIL] {e}")
        ok = False
    print()

    # --- Тест 3: ход с историей ---
    print("--- Тест 3: с историей ходов ---")
    cmd = ParsedCommand(
        action="talk",
        target="стражник",
        skill=None,
        roll_needed=False,
        difficulty="Ordinary",
        raw="Обращаюсь к стражнику",
    )
    history = [
        Turn(player="Иду к докам", master="Ты идёшь по коридору корабля..."),
        Turn(player="Осматриваю сундук", master="Ты находишь старый амулет..."),
    ]
    try:
        text = master.narrate(state, cmd, history=history)
        print(text)
        print()
        ok &= len(text) > 100
        print("[ ok ] история принята, ответ получен")
    except MasterError as e:
        print(f"[FAIL] {e}")
        ok = False

    print()
    if ok:
        print("ВСЕ ТЕСТЫ ПРОШЛИ.")
    else:
        print("ЕСТЬ ПАДЕНИЯ, см. выше.")
        sys.exit(1)


if __name__ == "__main__":
    main()
