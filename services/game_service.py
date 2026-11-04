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

        result = self.orch.process_turn(
            player_input, char, history=history, max_tokens=max_tokens
        )

        clean_text, applied_changes, updated_char = parse_and_apply(
            result.narrative, char
        )

        if applied_changes:
            save_character(login, char_name, updated_char)
            logger.info(
                f"State applied for {login}/{char_name}: "
                f"{', '.join(applied_changes)}"
            )

        roll_dict = result.roll.to_dict() if result.roll else None
        return clean_text, roll_dict, applied_changes, updated_char, result.command
