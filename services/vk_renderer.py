"""services/vk_renderer.py — Утилиты для VK-бота (картинки, текст)."""
import requests
import tempfile
import os

def clean_text_for_vk(text: str) -> str:
    """Убирает технические теги [STATE] и ROLLCARD, чтобы они не пугали игрока."""
    import re
    text = re.sub(r'\[STATE\].*?(?:\[/STATE\]|$)', '', text, flags=re.DOTALL)
    text = re.sub(r'<!--ROLLCARD:.*?-->', '', text, flags=re.DOTALL)
    return text.strip()

def get_status_text(char: dict) -> str:
    """Формирует текст для закрепленного сообщения (Статус)."""
    name = char.get("name", "Герой")
    faction = char.get("faction", "Неизвестно")
    hp_cur = char.get("wounds", {}).get("current", 0)
    hp_max = char.get("wounds", {}).get("max", 0)
    xp = char.get("xp", 0)
    loc = char.get("location", {}).get("place", "Неизвестно")
    
    return f"🛡️ **{name}** ({faction})\n❤️ HP: {hp_cur}/{hp_max} | ⭐ XP: {xp}\n📍 Локация: {loc}"

def upload_image_to_vk(vk, image_url: str) -> str:
    """Скачивает картинку и загружает её на сервера VK. Возвращает attachment."""
    try:
        # 1. Скачиваем картинку
        resp = requests.get(image_url, stream=True, timeout=15)
        resp.raise_for_status()
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
            temp_path = f.name

        # 2. Получаем сервер для загрузки
        upload_server = vk.photos.getMessagesUploadServer()
        upload_url = upload_server['upload_url']

        # 3. Загружаем
        with open(temp_path, 'rb') as f:
            files = {'photo': ('image.jpg', f)}
            upload_resp = requests.post(upload_url, files=files).json()

        # 4. Сохраняем на сервере ВК
        saved_photo = vk.photos.saveMessagesPhoto(
            server=upload_resp['server'],
            photo=upload_resp['photo'],
            hash=upload_resp['hash']
        )[0]

        # Очищаем временный файл
        os.unlink(temp_path)

        return f"photo{saved_photo['owner_id']}_{saved_photo['id']}"
    except Exception as e:
        print(f"[vk_renderer] Image upload failed: {e}")
        return None
