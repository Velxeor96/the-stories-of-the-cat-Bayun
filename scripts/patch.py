import sys
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

def apply_patch_128():
    print("=== PATCH_128: Fix SyntaxError + VK Bot Final Fixes ===")

    # ===== 1. ФИКС SYNTAXERROR В theme.py =====
    theme_path = ROOT / "ui" / "theme.py"
    if theme_path.exists():
        content = theme_path.read_text(encoding="utf-8")
        
        # Удаляем сломанный блок, который начинается с "import streamlit as _st"
        # и заканчивается на "unsafe_allow_html=True)" после многострочного CSS
        pattern = r"import streamlit as _st\s*\n\s*_st\.markdown\('<style>[\s\S]*?</style>', unsafe_allow_html=True\)"
        match = re.search(pattern, content)
        if match:
            content = content[:match.start()] + content[match.end():]
            print("[+] Удалён сломанный блок PATCH_127 из theme.py")
        else:
            print("[!] Сломанный блок не найден (возможно, уже исправлен)")
        
        # Добавляем корректный CSS одной строкой (без переносов)
        css = ".block-container { padding-top: 0rem !important; padding-bottom: 0rem !important; margin-top: 0rem !important; max-width: 100% !important; } header[data-testid=\"stHeader\"] { display: none !important; }"
        # Экранируем двойные кавычки для Python-строки
        css_escaped = css.replace('"', '\\"')
        block = f"\n# PATCH_128: Full-screen splash fix\nimport streamlit as _st_fix\n_st_fix.markdown('<style>{css_escaped}</style>', unsafe_allow_html=True)\n"
        
        if "# PATCH_128" not in content:
            content += block
            print("[+] Добавлен корректный CSS для Splash (одной строкой)")
        else:
            print("[!] Блок PATCH_128 уже присутствует")
            
        theme_path.write_text(content, encoding="utf-8")
        print("[+] theme.py сохранён")

    # ===== 2. ФИКС BOT_VK.PY (добиваем оставшиеся 3 фикса) =====
    bot_path = ROOT / "bot_vk.py"
    if not bot_path.exists():
        print("[-] bot_vk.py не найден!")
        return
        
    content = bot_path.read_text(encoding="utf-8")
    changes = 0

    # 2.1 Тираниды в FACTIONS
    if '"Тираниды"' not in content:
        content = re.sub(
            r'("Некроны":\s*"necrons",?)',
            r'\1\n    "Тираниды":  "tyranids",',
            content
        )
        changes += 1
        print("[+] Тираниды добавлены в FACTIONS")

    # 2.2 Статы 30 -> 22
    # Ищем любой словарь stats с "WS": 30 и заменяем на 22
    if '"WS": 30' in content:
        content = re.sub(
            r'stats\s*=\s*\{[^\}]+\}',
            'stats = {"WS": 22, "BS": 22, "S": 22, "T": 22, "Ag": 22, "Int": 22, "Per": 22, "WP": 22, "Fel": 22}',
            content
        )
        changes += 1
        print("[+] Статы заменены на 22 (лимит 200)")

    # 2.3 Проверка isinstance перед генерацией аватарки
    if "isinstance(char_data, dict)" not in content:
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

    # 2.4 Обработка кнопки "Настройки"
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
    apply_patch_128()