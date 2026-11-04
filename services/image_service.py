"""services/image_service.py — Генерация иллюстраций."""
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
