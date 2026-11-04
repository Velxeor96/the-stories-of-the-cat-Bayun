import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

def apply_patch_123():
    print("=== PATCH_123: Multimedia 2.0 — Avatars ===")

    # 1. Обновляем services/image_service.py
    img_path = ROOT / "services" / "image_service.py"
    if img_path.exists():
        content = img_path.read_text(encoding="utf-8")
        
        # Добавляем функцию generate_avatar_url и обновляем generate_image
        new_code = r'''"""services/image_service.py — Генерация иллюстраций."""
import urllib.parse
import hashlib
import streamlit as st

def generate_image(prompt: str, seed: int = None) -> str:
    """Генерирует изображение и возвращает URL. 
    По умолчанию использует Pollinations.ai (бесплатно, без ключей).
    
    PATCH_123: Для перехода на Kandinsky замените реализацию этой функции 
    на вызов API Сбера (например, через requests.post).
    """
    clean_prompt = "Warhammer 40k, grimdark, " + prompt.replace('[', '').replace(']', '')
    encoded = urllib.parse.quote(clean_prompt[:400])
    
    if seed is None:
        seed = st.session_state.get("_img_seed", 42)
    
    return f"https://image.pollinations.ai/prompt/{encoded}?width=1024&height=576&nologo=true&seed={seed}"

def generate_avatar_url(char_data: dict) -> str:
    """Генерирует URL аватарки для персонажа."""
    name = char_data.get("name", "hero")
    race = char_data.get("faction", "imperium")
    gender = char_data.get("gender", "male")
    appearance = char_data.get("appearance", "")
    
    prompt = f"Portrait of a {race} {gender} named {name}, {appearance}, Warhammer 40k style, grimdark, highly detailed, character portrait"
    
    # Уникальный seed на основе имени, чтобы картинка была стабильной
    seed = int(hashlib.md5(name.encode()).hexdigest()[:8], 16) % 100000
    return generate_image(prompt, seed=seed)
'''
        img_path.write_text(new_code, encoding="utf-8")
        print("[+] image_service.py обновлен (добавлен generate_avatar_url)")

    # 2. Обновляем ui/screens/wizard.py
    wiz_path = ROOT / "ui" / "screens" / "wizard.py"
    if wiz_path.exists():
        content = wiz_path.read_text(encoding="utf-8")
        
        # 2.1. Генерация аватарки при сохранении
        old_save = r'''            data = validate_and_build(
                name=name.strip(), gender=gender, age=str(age),
                appearance=appearance, user_background=user_background,
                faction_id=faction_id, subfaction_id=subfaction_id,
                home_world_id=home_world_id, career_id=career_id,
                stats_dict=raw,
            )
            save_character(login, name.strip(), data)'''
        
        new_save = r'''            data = validate_and_build(
                name=name.strip(), gender=gender, age=str(age),
                appearance=appearance, user_background=user_background,
                faction_id=faction_id, subfaction_id=subfaction_id,
                home_world_id=home_world_id, career_id=career_id,
                stats_dict=raw,
            )
            
            # PATCH_123: Генерация аватарки
            from services.image_service import generate_avatar_url
            with st.spinner("🎨 Создаем портрет..."):
                data["avatar_url"] = generate_avatar_url(data)
                
            save_character(login, name.strip(), data)'''
        
        if "generate_avatar_url" not in content:
            if old_save in content:
                content = content.replace(old_save, new_save)
                print("[+] wizard.py: добавлена генерация аватарки при сохранении")
            else:
                print("[-] wizard.py: не найден блок сохранения персонажа")
        
        # 2.2. Отображение аватарок в списке персонажей
        old_list = r'''        with st.expander("Персонажи (" + str(len(existing)) + ")"):
            for nm in existing:
                c1, c2 = st.columns([4, 1])
                with c1:
                    st.markdown("**" + nm + "**")
                with c2:
                    if st.button("Играть", key="play_" + nm, width="stretch"):
                        st.session_state.active_character = nm
                        _goto("game")
                        st.rerun()'''
        
        new_list = r'''        with st.expander("Персонажи (" + str(len(existing)) + ")"):
            for nm in existing:
                c1, c2 = st.columns([4, 1])
                with c1:
                    # PATCH_123: Показываем аватарку
                    try:
                        from persistence.characters import load_character
                        _cd = load_character(login, nm)
                        _av = _cd.get("avatar_url")
                        if _av:
                            c_img, c_txt = st.columns([1, 4])
                            with c_img:
                                st.image(_av, width=60)
                            with c_txt:
                                st.markdown("**" + nm + "**")
                        else:
                            st.markdown("**" + nm + "**")
                    except Exception:
                        st.markdown("**" + nm + "**")
                with c2:
                    if st.button("Играть", key="play_" + nm, width="stretch"):
                        st.session_state.active_character = nm
                        _goto("game")
                        st.rerun()'''
        
        if "PATCH_123: Показываем аватарку" not in content:
            if old_list in content:
                content = content.replace(old_list, new_list)
                print("[+] wizard.py: добавлено отображение аватарок в списке")
            else:
                print("[-] wizard.py: не найден блок списка персонажей")
        
        wiz_path.write_text(content, encoding="utf-8")

    # 3. Обновляем ui/screens/game.py (сайдбар)
    game_path = ROOT / "ui" / "screens" / "game.py"
    if game_path.exists():
        content = game_path.read_text(encoding="utf-8")
        
        old_sidebar = r'''    with st.sidebar:
        st.markdown("### " + str(char.get("name", "—")))'''
        
        new_sidebar = r'''    with st.sidebar:
        # PATCH_123: Аватарка в сайдбаре
        _av = char.get("avatar_url")
        if _av:
            st.image(_av, width=100)
        
        st.markdown("### " + str(char.get("name", "—")))'''
        
        if "PATCH_123: Аватарка" not in content:
            if old_sidebar in content:
                content = content.replace(old_sidebar, new_sidebar)
                game_path.write_text(content, encoding="utf-8")
                print("[+] game.py: добавлена аватарка в сайдбар")
            else:
                print("[-] game.py: не найден блок сайдбара")

if __name__ == "__main__":
    apply_patch_123()
    print("=== Готово ===")