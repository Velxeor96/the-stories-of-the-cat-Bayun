"""bot_vk.py — VK Rich Bot для WH40K RPG (PATCH_124)."""
import os
import json
import random
import time
import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from dotenv import load_dotenv

from core.config import Config
from services.game_service import GameService
from services.orchestrator import Orchestrator
from services.character_service import validate_and_build
from services.image_service import generate_image, generate_avatar_url
from services.vk_renderer import clean_text_for_vk, get_status_text, upload_image_to_vk
from persistence.characters import save_character, list_characters, load_character
from persistence.chats import load_history, append_turn, save_history
from persistence.accounts import register_user

load_dotenv()
TOKEN = os.getenv("VK_TOKEN")
if not TOKEN:
    raise ValueError("VK_TOKEN не задан в .env!")

vk_session = vk_api.VkApi(token=TOKEN)
vk = vk_session.get_api()
longpoll = VkLongPoll(vk_session)

config = Config.load()
orchestrator = Orchestrator(config, use_rag=True)
game_service = GameService(orchestrator)

USER_STATES = {}

def _safe_set_activity(user_id, activity_type="typing"):
    try:
        vk.messages.setActivity(user_id=user_id, type=activity_type)
    except Exception as e:
        print(f"[VK] setActivity fail: {e}")


def get_menu_keyboard():
    kb = VkKeyboard(one_time=False)
    kb.add_button("📊 Статус", color=VkKeyboardColor.SECONDARY)
    kb.add_button("🎒 Инвентарь", color=VkKeyboardColor.SECONDARY)
    kb.add_line()
    kb.add_button("⚙️ Настройки", color=VkKeyboardColor.SECONDARY)
    return kb.get_keyboard()

def send_msg(user_id, text, attachment=None, keyboard=None):
    chunks = [text[i:i+4000] for i in range(0, len(text), 4000)]
    for i, chunk in enumerate(chunks):
        vk.messages.send(
            user_id=user_id,
            message=chunk,
            attachment=attachment if i == 0 else None,
            random_id=random.randint(1, 2**31),
            keyboard=keyboard if i == len(chunks)-1 else None
        )
        time.sleep(0.3) # Защита от флуд-контроля

def update_pinned_status(user_id, char):
    """Обновляет закрепленное сообщение со статусом."""
    status_text = get_status_text(char)
    try:
        # Отправляем статус
        msg_id = vk.messages.send(user_id=user_id, message=status_text, random_id=0)
        # Закрепляем
        vk.messages.pin(peer_id=user_id, message_id=msg_id)
    except Exception as e:
        print(f"[VK] Pin error: {e}")

print("VK Rich Bot запущен...")

for event in longpoll.listen():
    if event.type == VkEventType.MESSAGE_NEW and event.to_me:
        user_id = event.user_id
        text = event.text.strip()
        login = f"vk_{user_id}"
        
        if not text:
            continue

        state = USER_STATES.get(user_id, {"step": "idle"})

        # --- Команда START ---
        if text.lower() in ("начать", "start", "/start"):
            try:
                register_user(login, "vk_password")
            except Exception:
                pass
                
            chars = list_characters(login)
            if chars:
                USER_STATES[user_id] = {"step": "choose_char"}
                kb = VkKeyboard(one_time=True)
                for c in chars:
                    kb.add_button(c, color=VkKeyboardColor.SECONDARY)
                    kb.add_line()
                kb.add_button("Создать нового", color=VkKeyboardColor.PRIMARY)
                send_msg(user_id, "С возвращением! Выбери персонажа:", keyboard=kb.get_keyboard())
            else:
                USER_STATES[user_id] = {"step": "choose_faction"}
                kb = VkKeyboard(one_time=True)
                kb.add_button("Империум", color=VkKeyboardColor.PRIMARY)
                kb.add_button("Эльдары", color=VkKeyboardColor.PRIMARY)
                kb.add_line()
                kb.add_button("Тау", color=VkKeyboardColor.PRIMARY)
                kb.add_button("Некроны", color=VkKeyboardColor.PRIMARY)
                send_msg(user_id, "Приветствую! Выбери свою фракцию:", keyboard=kb.get_keyboard())
            continue

        # --- Создание персонажа ---
        if state["step"] == "choose_faction":
            faction_map = {"Империум": "imperium", "Эльдары": "eldar", "Тау": "tau", "Некроны": "necrons"
    "Тираниды":  "tyranids",}
            faction_id = faction_map.get(text)
            if not faction_id:
                send_msg(user_id, "Выбери фракцию с помощью кнопок.")
                continue
            state["faction_id"] = faction_id
            state["step"] = "enter_name"
            USER_STATES[user_id] = state
            send_msg(user_id, f"Ты выбрал {text}. Напиши имя своего персонажа:")
            continue

        if state["step"] == "enter_name":
            char_name = text
            faction_id = state["faction_id"]
            # 9 статов по 22 = 198 очков (лимит 200)
            stats = {"WS": 22, "BS": 22, "S": 22, "T": 22, "Ag": 22, "Int": 22, "Per": 22, "WP": 22, "Fel": 22}
            try:
                # Получаем первые доступные родной мир и карьеру для фракции
                from services.module_loader import get_faction_data
                f_data = get_faction_data(faction_id)
                hws = f_data.get("home_worlds", [])
                careers = f_data.get("archetypes", [])
                
                hw_id = hws[0]["id"] if hws else None
                career_id = careers[0]["id"] if careers else None

                char_data = validate_and_build(
                    name=char_name, gender="male", age="30",
                    appearance="", user_background="Прибыл через VK.",
                    faction_id=faction_id, subfaction_id=None,
                    home_world_id=hw_id, career_id=career_id, stats_dict=stats
                )
                
                # PATCH_126: Защита от возврата строки вместо словаря
                if not isinstance(char_data, dict):
                    send_msg(user_id, f"⚠️ Не удалось создать персонажа: {char_data}")
                    USER_STATES[user_id] = {"step": "idle"}
                    continue

                send_msg(user_id, "🎨 Создаем портрет персонажа...")
                char_data["avatar_url"] = generate_avatar_url(char_data)
                save_character(login, char_name, char_data)
                save_history(login, char_name, [])
                
                USER_STATES[user_id] = {"step": "playing", "char_name": char_name}
                update_pinned_status(user_id, char_data)
                
                # Отправляем аватарку
                avatar_att = upload_image_to_vk(vk, char_data["avatar_url"])
                send_msg(user_id, f"Персонаж **{char_name}** готов к приключениям!", attachment=avatar_att, keyboard=get_menu_keyboard())
            except Exception as e:
                send_msg(user_id, f"Ошибка: {e}")
                USER_STATES[user_id] = {"step": "idle"}
            continue

        # --- Выбор персонажа ---
        if state["step"] == "choose_char":
            if text == "Создать нового":
                USER_STATES[user_id] = {"step": "choose_faction"}
                kb = VkKeyboard(one_time=True)
                kb.add_button("Империум", color=VkKeyboardColor.PRIMARY)
                kb.add_button("Эльдары", color=VkKeyboardColor.PRIMARY)
                kb.add_line()
                kb.add_button("Тау", color=VkKeyboardColor.PRIMARY)
                kb.add_button("Некроны", color=VkKeyboardColor.PRIMARY)
                send_msg(user_id, "Выбери фракцию:", keyboard=kb.get_keyboard())
            else:
                USER_STATES[user_id] = {"step": "playing", "char_name": text}
                char = load_character(login, text)
                update_pinned_status(user_id, char)
                send_msg(user_id, f"Загружен персонаж: {text}. Продолжаем!", keyboard=get_menu_keyboard())
            continue

        # --- Меню (Статус, Инвентарь) ---
        if text == "📊 Статус":
            char_name = state.get("char_name")
            if char_name:
                char = load_character(login, char_name)
                update_pinned_status(user_id, char)
                send_msg(user_id, "Статус обновлен (смотри закрепленное сообщение).")
            continue

        if text == "⚙️ Настройки":
            send_msg(user_id, "⚙️ Настройки в разработке. Скоро!")
            continue

        if text == "🎒 Инвентарь":
            char_name = state.get("char_name")
            if char_name:
                char = load_character(login, char_name)
                equip = char.get("equipment", [])
                weapons = char.get("weapons", [])
                inv_text = "🎒 **Инвентарь:**\n"
                for w in weapons: inv_text += f"⚔️ {w.get('name', w)}\n"
                for e in equip: inv_text += f"📦 {e}\n"
                if not weapons and not equip: inv_text += "Пусто."
                send_msg(user_id, inv_text)
            continue

        # --- Игровой процесс ---
        if state["step"] == "playing":
            char_name = state["char_name"]
            history = load_history(login, char_name)
            
            # Индикатор набора
            _safe_set_activity(user_id, "typing")
            
            if not history:
                try:
                    char = load_character(login, char_name)
                    res = orchestrator.process_turn("Начало приключения.", char, history=[])
                    clean = clean_text_for_vk(res.narrative)
                    append_turn(login, char_name, "Начало приключения.", res.narrative)
                    
                    # Генерируем картинку к первой сцене
                    img_url = generate_image(clean[-300:])
                    att = upload_image_to_vk(vk, img_url)
                    
                    update_pinned_status(user_id, char)
                    send_msg(user_id, clean, attachment=att, keyboard=get_menu_keyboard())
                except Exception as e:
                    send_msg(user_id, f"Ошибка старта: {e}")
                continue

            # Обычный ход
            try:
                clean_text, roll_dict, applied, char, cmd = game_service.process_player_action(
                    login, char_name, text, history, 700
                )
                
                packed = clean_text
                if roll_dict:
                    packed += "\n<!--ROLLCARD:" + json.dumps(roll_dict, ensure_ascii=False) + "-->"
                append_turn(login, char_name, text, packed)
                
                display_text = clean_text_for_vk(packed)
                
                # Если были изменения (урон, лут) - обновляем закреп
                if applied:
                    update_pinned_status(user_id, char)
                
                # Генерируем картинку
                _safe_set_activity(user_id, "typing")
                img_url = generate_image(display_text[-300:])
                att = upload_image_to_vk(vk, img_url)
                
                send_msg(user_id, display_text, attachment=att, keyboard=get_menu_keyboard())
                
            except Exception as e:
                print(f"[VK] Game error: {e}")
                send_msg(user_id, "Мастер задумался... Попробуй переформулировать действие.")
            continue

        send_msg(user_id, "Напиши /start, чтобы начать.")
