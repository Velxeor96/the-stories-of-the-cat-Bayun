from services.orchestrator import Orchestrator
from services.state_manager import parse_and_apply
from persistence.characters import load_character, save_character
from core.logger import get_logger

logger = get_logger(__name__)


class GameService:
    def __init__(self, orchestrator: Orchestrator):
        self.orch = orchestrator

    def process_player_action(self, login: str, char_name: str,
                              player_input: str, history: list,
                              max_tokens: int):
        char = load_character(login, char_name)

        try:
            result = self.orch.process_turn(
                player_input, char, history=history, max_tokens=max_tokens
            )
        except Exception as e:
            logger.error(f"Orchestrator failed: {e}")
            # Возвращаем безопасный фоллбек, чтобы UI не падал
            return "[Ошибка Мастера] Произошла системная ошибка. Попробуйте еще раз.", None, [], char, None

        clean_text, applied_changes, updated_char = parse_and_apply(
            result.narrative, char
        )

        # PATCH_121: Автоматическая запись в память мира
        import re
        _memory_triggers = [r"\bубит\b", r"\bмертв\b", r"\bпогиб\b", r"\bуничтожен\b", r"\bвыполнен\b"]
        if any(re.search(t, clean_text, re.IGNORECASE) for t in _memory_triggers):
            from services.world_memory import add_memory
            # Берем первое предложение, где сработал триггер
            for sentence in re.split(r'(?<=[.!?]) +', clean_text):
                if any(re.search(t, sentence, re.IGNORECASE) for t in _memory_triggers):
                    add_memory(login, char_name, sentence.strip())
                    break

        if applied_changes:
            save_character(login, char_name, updated_char)
            logger.info(
                f"State applied for {login}/{char_name}: "
                f"{', '.join(applied_changes)}"
            )

        roll_dict = result.roll.to_dict() if result.roll else None
        return clean_text, roll_dict, applied_changes, updated_char, result.command

    def process_player_action_stream(self, login: str, char_name: str,
                                     player_input: str, history: list,
                                     max_tokens: int, meta_out: dict = None):
        """Стриминговый ход. Накапливает текст, чтобы вытащить [STATE]."""
        if meta_out is None:
            meta_out = {}
            
        char = load_character(login, char_name)
        full_text = ""
        
        for chunk in self.orch.process_turn_stream(
            player_input, char, history=history, max_tokens=max_tokens, meta_out=meta_out
        ):
            full_text += chunk
            yield chunk
            
        # После окончания стрима парсим [STATE]
        from services.state_manager import parse_and_apply
        clean_text, applied_changes, updated_char = parse_and_apply(full_text, char)
        
        if applied_changes:
            save_character(login, char_name, updated_char)
            logger.info(f"State applied for {login}/{char_name}: {', '.join(applied_changes)}")
            
        meta_out['clean_text'] = clean_text
        meta_out['applied_changes'] = applied_changes
        meta_out['updated_char'] = updated_char
