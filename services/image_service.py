"""services/image_service.py — Генерация иллюстраций (Streamlit + VK)."""
import urllib.parse
import hashlib
import random


def _get_seed(seed=None) -> int:
    if seed is not None:
        return int(seed)
    try:
        import streamlit as st
        return int(st.session_state.get("_img_seed", 42))
    except Exception:
        return random.randint(1, 100000)


def generate_image(prompt, seed=None) -> str:
    clean_prompt = "Warhammer 40k, grimdark, " + prompt.replace("[", "").replace("]", "")
    encoded = urllib.parse.quote(clean_prompt[:400])
    actual_seed = _get_seed(seed)
    base = "https://image.pollinations.ai/prompt/"
    return base + encoded + "?width=1024&height=576&nologo=true&seed=" + str(actual_seed)


def generate_avatar_url(char_data) -> str:
    name = char_data.get("name", "hero")
    race = char_data.get("faction", "imperium")
    gender = char_data.get("gender", "male")
    appearance = char_data.get("appearance", "")
    prompt = "Portrait of a " + race + " " + gender + " named " + name + ", " + appearance + ", Warhammer 40k, grimdark"
    seed = int(hashlib.md5(name.encode()).hexdigest()[:8], 16) % 100000
    return generate_image(prompt, seed=seed)
