import sys
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

def apply_patch_127():
    print("=== PATCH_127: UI Fix & VK Bot Regex Fix ===")

    # ===== 1. ФИКС UI (убираем отступ сверху и скрываем хедер) =====
    theme_path = ROOT / "ui" / "theme.py"
    if theme_path.exists():
        content = theme_path.read_text(encoding="utf-8")
        css_fix = """
/* PATCH_127: Полноэкранный режим для Splash */
.block-container {
    padding-top: 0rem !important;
    padding-bottom: 0rem !important;
    margin-top: 0rem !important;
    max-width: 100% !important;
}
header[data-testid="stHeader"] {
    display: none !important;
}
"""
        if "PATCH_127" not in content:
            # Добавляем в конец файла, чтобы переопределить старые стили
            content += f"\nimport streamlit as _st\n_st.markdown('<style>{css_fix}</style>', unsafe_allow_html=True)\n"
            theme_path.write_text(content, encoding="utf-8")
            print("[+] theme.py: убраны отступы сверху (фикс Splash)")
        else:
            print("[!] theme.py: фикс уже применен")

    # ===== 2. ФИКС BOT_VK.PY (через регулярки) =====
    bot_path = ROOT / "bot_vk.py"
    if not bot_path.exists():
        print("[-] bot_vk.py не найден!")
        return
        
    content = bot_path.read_text(encoding="utf-8")
    changes = 0

    # 2.1 Тираниды в FACTIONS (ищем словарь)
    if '"Тираниды"' not in content:
        content = re.sub(
            r'("Некроны":\s*"necrons",?)',
            r'\1\n    "Тираниды":  "tyranids",',
            content
        )
        changes += 1
        print("[+] Тираниды добавлены в FACTIONS")

    # 2.2 Статы 30 -> 22 (ищем любой словарь со статами)
    # Ищем: stats = {"WS": 30, ...}
    if '"WS": 30' in content:
        content = re.sub(
            r'stats\s*=\s*\{[^\}]+\}',
            'stats = {"WS": 22, "BS": 22, "S": 22, "T": 22, "Ag": 22, "Int": 22, "Per": 22, "WP": 22, "Fel": 22}',
            content
        )
        changes += 1
        print("[+] Статы заменены на 22 (лимит 200)")

    # 2.3 Проверка isinstance (защита от строки)
    if "isinstance(char_data, dict)" not in content:
        # Ищем вызов generate_avatar_url и вставляем проверку перед ним
        pattern = r'(send_msg\(user_id,\s*"🎨 Создаем портрет персонажа\.\.\."\))'
        replacement = (
            'if not isinstance(char_data, dict):\n'
            '                    send_msg(user_id, f"⚠️ Ошибка создания: {char_data}")\n'
            '                    USER_STATES[user_id] = {"step": "idle"}\n'
            '                    continue\n'
            '                \\1'
        )
        content = re.sub(pattern, replacement, content, count=1)
        changes += 1
        print("[+] Добавлена проверка isinstance(char_data, dict)")

    # 2.4 Обработка кнопки Настройки
    if 'if text == "⚙️ Настройки":' not in content:
        pattern = r'(if text == "🎒 Инвентарь":)'
        replacement = (
            'if text == "⚙️ Настройки":\n'
            '            send_msg(user_id, "⚙️ Настройки в разработке. Скоро!")\n'
            '            continue\n\n'
            '        \\1'
        )
        content = re.sub(pattern, replacement, content, count=1)
        changes += 1
        print("[+] Обработка кнопки Настройки")

    bot_path.write_text(content, encoding="utf-8")
    print(f"[+] bot_vk.py сохранён (изменений: {changes})")
    print("=== Готово ===")

if __name__ == "__main__":
    apply_patch_127()