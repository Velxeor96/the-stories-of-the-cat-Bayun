r"""
Тестовый запрос к LLM через KodikRouter.

Проверяет, что:
  - config.yaml читается
  - ключ из secrets.toml подхватывается
  - KodikRouter отвечает
  - модель deepseek/deepseek-v4-flash-latest работает

Запуск (из корня проекта):
    python scripts\test_llm.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.config import Config  # noqa: E402


def main() -> None:
    print("=== Загрузка конфига ===")
    cfg = Config.load()
    print(cfg.summary())
    print()

    # Получаем URL и ключ для провайдера kodik
    try:
        base_url = cfg.provider_url("kodik")
        api_key = cfg.provider_key("kodik")
        model_id = cfg.model_id("deepseek_flash")
    except Exception as e:
        print(f"[ERR] Конфиг не готов: {e}")
        sys.exit(1)

    print(f"Base URL: {base_url}")
    print(f"Ключ:     {api_key[:8]}... (обрезан)")
    print(f"Модель:   {model_id}")
    print()

    # Импорт openai
    try:
        from openai import OpenAI
    except ImportError:
        print("[ERR] Нет пакета openai. Установи: pip install openai")
        sys.exit(1)

    client = OpenAI(api_key=api_key, base_url=base_url)

    print("=== Отправляю тестовый запрос ===")
    try:
        resp = client.chat.completions.create(
            model=model_id,
            messages=[
                {"role": "system", "content": "Ты — тестовый ассистент. Отвечай кратко."},
                {"role": "user", "content": "Привет! Ответь одним предложением по-русски."},
            ],
            temperature=0.7,
            max_tokens=100,
        )
    except Exception as e:
        print(f"[ERR] Запрос упал: {type(e).__name__}: {e}")
        sys.exit(1)

    msg = resp.choices[0].message.content
    usage = resp.usage

    print()
    print("=== ОТВЕТ МОДЕЛИ ===")
    print(msg)
    print()
    print("=== Расход ===")
    print(f"Вход:  {usage.prompt_tokens} токенов")
    print(f"Выход: {usage.completion_tokens} токенов")
    print(f"Всего: {usage.total_tokens} токенов")
    print()
    print("ВСЁ РАБОТАЕТ.")


if __name__ == "__main__":
    main()