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
        # Специфичные промпты для рас
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

    prompt = "Portrait of a " + race_desc + ", " + gender + ", named " + name + ", " + appearance + ", Warhammer 40k style, grimdark, highly detailed character art"
    seed = int(hashlib.md5(name.encode()).hexdigest()[:8], 16) % 100000
    return generate_image(prompt, seed=seed)
