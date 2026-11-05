import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

def apply_patch_129():
    print("=== PATCH_129: Stability, Performance & Avatars ===")

    # ===== 1. ФИКС NameError В game.py =====
    game_path = ROOT / "ui" / "screens" / "game.py"
    if game_path.exists():
        content = game_path.read_text(encoding="utf-8")
        # Ищем проблемную строку и заменяем на безопасный fallback
        old_str = "clean_text = meta.get('clean_text', response_text)"
        new_str = "clean_text = meta.get('clean_text', '')"
        if old_str in content:
            content = content.replace(old_str, new_str)
            print("[+] game.py: исправлен NameError (response_text -> '')")
        else:
            print("[!] game.py: строка с response_text не найдена (возможно, уже исправлена)")
        game_path.write_text(content, encoding="utf-8")

    # ===== 2. КЭШИРОВАНИЕ RAG ДЛЯ СКОРОСТИ =====
    rag_path = ROOT / "services" / "rag.py"
    if rag_path.exists():
        content = rag_path.read_text(encoding="utf-8")
        # Добавляем st.cache_resource, если его нет
        if "@st.cache_resource" not in content:
            # Ищем функцию get_kb и добавляем декоратор
            old_kb = "def get_kb() -> KnowledgeBase:"
            new_kb = "import streamlit as st\n\n@st.cache_resource\ndef get_kb() -> KnowledgeBase:"
            if old_kb in content:
                content = content.replace(old_kb, new_kb)
                print("[+] rag.py: добавлено кэширование RAG (ускорит клики)")
            else:
                print("[-] rag.py: не найдена функция get_kb")
        else:
            print("[!] rag.py: кэширование уже есть")
        rag_path.write_text(content, encoding="utf-8")

    # ===== 3. УЛУЧШЕНИЕ АВАТАРОК =====
    img_path = ROOT / "services" / "image_service.py"
    if img_path.exists():
        content = img_path.read_text(encoding="utf-8")
        old_prompt = 'prompt = "Portrait of a " + race + " " + gender + " named " + name + ", " + appearance + ", Warhammer 40k, grimdark"'
        
        new_prompt = r'''    # Специфичные промпты для рас
    race_lower = race.lower()
    race_desc = "human"
    if "eldar" in race_lower:
        race_desc = "slender alien Eldar with pointed ears and elegant bone armor"
    elif "necron" in race_lower:
        race_desc = "skeletal robot Necron with glowing green eyes and metallic body"
    elif "tau" in race_lower:
        race_desc = "blue-skinned alien Tau with hooves and smooth armor"
    elif "tyranid" in race_lower:
        race_desc = "monstrous insectoid alien Tyranid with chitin armor and claws"

    prompt = "Portrait of a " + race_desc + ", " + gender + ", named " + name + ", " + appearance + ", Warhammer 40k style, grimdark, highly detailed character art"'''
        
        if old_prompt in content:
            content = content.replace(old_prompt, new_prompt)
            print("[+] image_service.py: обновлены промпты для рас (Эльдары, Некроны и т.д.)")
        else:
            print("[-] image_service.py: старый промпт не найден")
        img_path.write_text(content, encoding="utf-8")

    # 4. УВЕЛИЧЕНИЕ РАЗМЕРА АВАТАРКИ В САЙДБАРЕ
    if game_path.exists():
        content = game_path.read_text(encoding="utf-8")
        old_img = 'st.image(_av, width=100)'
        new_img = 'st.image(_av, use_container_width=True)'
        if old_img in content:
            content = content.replace(old_img, new_img)
            game_path.write_text(content, encoding="utf-8")
            print("[+] game.py: аватарка растянута на всю ширину сайдбара")

    print("\n=== Готово ===")
    print("ПРОВЕРЬ СИНТАКСИС: python -c \"compile(open('ui/screens/game.py', encoding='utf-8').read(), 'game.py', 'exec')\"")

if __name__ == "__main__":
    apply_patch_129()