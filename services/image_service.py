"""services/image_service.py — Генерация иллюстраций."""
import urllib.parse
import streamlit as st

def generate_image(prompt: str) -> str:
    """Генерирует изображение и возвращает URL. 
    По умолчанию использует Pollinations.ai (бесплатно, без ключей).
    
    PATCH_123: Для перехода на Kandinsky замените реализацию этой функции 
    на вызов API Сбера (например, через requests.post).
    """
    # Очищаем промпт от служебных символов
    clean_prompt = "Warhammer 40k, grimdark, " + prompt.replace('[', '').replace(']', '')
    encoded = urllib.parse.quote(clean_prompt[:400]) # Ограничиваем длину
    
    # Генерируем случайный seed, чтобы картинки не повторялись
    seed = st.session_state.get("_img_seed", 42)
    
    return f"https://image.pollinations.ai/prompt/{encoded}?width=1024&height=576&nologo=true&seed={seed}"
