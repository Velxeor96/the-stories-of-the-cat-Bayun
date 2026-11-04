"""bot_vk.py — VK-бот (SQLite + GameService)."""
import os
import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
from dotenv import load_dotenv

from core.config import Config
from core.logger import get_logger
from services.orchestrator import Orchestrator
from services.game_service import GameService
from services.character_creation import build_character
from persistence.characters import load_character, save_character
from persistence.chats import load_history, append_turn
from persistence.db import init_db

logger = get_logger(__name__)

load_dotenv()
TOKEN = os.getenv("VK_TOKEN")
if not TOKEN:
    raise ValueError("VK_TOKEN не задан в .env!")

vk_session = vk_api.VkApi(token=TOKEN)
vk = vk_session.get_api()
longpoll = VkLongPoll(vk_session)

config = Config()
orchestrator = Orchestrator(config)
game_service = GameService(orchestrator)

init_db()


def send_msg(user_id, text):
    chunks = [text[i:i+4000] for i in range(0, len(text), 4000)]
    for chunk in chunks:
        vk.messages.send(user_id=user_id, message=chunk, random_id=0)


def get_or_create_vk_character(login: str) -> str:
    char_name = "Странник"
    try:
        load_character(login, char_name)
        return char_name
    except Exception:
        pass

    try:
        char = build_character(
            name=char_name, gender="male", age="30",
            appearance="Странник", user_background="",
            faction_id="imperium", subfaction_id=None,
            home_world_id=None, career_id=None,
            characteristics={
                "WS": 30, "BS": 30, "S": 30, "T": 30, "Ag": 30,
                "Int": 30, "Per": 30, "WP": 30, "Fel": 30,
            },
        )
        save_character(login, char_name, char)
        logger.info(f"Created full VK character for {login}")
    except Exception as e:
        logger.error(f"VK character creation failed for {login}: {e}",
                     exc_info=True)
    return char_name


logger.info("VK Бот запущен и слушает сообщения...")


for event in longpoll.listen():
    if event.type == VkEventType.MESSAGE_NEW and event.to_me:
        user_id = str(event.user_id)
        login = f"vk_{user_id}"
        text = event.text.strip()

        if not text:
            continue

        if text.lower() in ("начать", "start", "/start"):
            send_msg(event.user_id,
                     "Приветствую, странник. Это WH40K RPG.\n\n"
                     "Напиши любое действие, чтобы начать.")
            continue

        char_name = get_or_create_vk_character(login)
        history = load_history(login, char_name)

        try:
            clean_text, roll_dict, applied, updated_char, _cmd = (
                game_service.process_player_action(
                    login=login,
                    char_name=char_name,
                    player_input=text,
                    history=history,
                    max_tokens=700,
                )
            )

            append_turn(login, char_name, text, clean_text)

            if roll_dict:
                verdict = "УСПЕХ" if roll_dict.get("success") else "ПРОВАЛ"
                clean_text += (
                    f"\n\n[Бросок: {roll_dict.get('roll')} "
                    f"vs {roll_dict.get('target')} -> {verdict}]"
                )

            send_msg(event.user_id, clean_text)

        except Exception as e:
            logger.error(f"VK Bot error for {user_id}: {e}", exc_info=True)
            send_msg(event.user_id, "Мастер задумался... Попробуйте позже.")
