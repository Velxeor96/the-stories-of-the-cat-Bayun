import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

def apply_patch_122():
    print("=== PATCH_122: Streaming & Image Architecture ===")

    # 1. Создаем services/image_service.py (Архитектура под Kandinsky)
    img_path = ROOT / "services" / "image_service.py"
    img_code = r'''"""services/image_service.py — Генерация иллюстраций."""
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
'''
    if not img_path.exists():
        img_path.write_text(img_code, encoding="utf-8")
        print("[+] Создан services/image_service.py (заготовка под Kandinsky)")

    # 2. master.py: Добавляем narrate_stream
    master_path = ROOT / "services" / "master.py"
    if master_path.exists():
        content = master_path.read_text(encoding="utf-8")
        
        stream_method = r'''
    def narrate_stream(self, state, command, *, roll=None, history=None,
                       extra_context="", max_tokens=700):
        """Генератор для стриминга ответа."""
        msg = self._build_message(state=state, command=command, roll=roll,
                                  history=history or [], extra_context=extra_context)
        client = make_client(provider_key=self.model.provider,
                             api_key=self.api_key, base_url=self.base_url)
        try:
            response = client.chat.completions.create(
                model=self.model.id,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": msg},
                ],
                temperature=0.85, max_tokens=max_tokens,
                stream=True
            )
            for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            print("[master] stream fail: " + type(e).__name__)
            yield "[fallback-мастер] Попробуй переформулировать ход."

    def _do_request(self, *, system_prompt, user_message, model,
                    temperature, max_tokens):'''
        
        if "def narrate_stream" not in content:
            content = content.replace("    def _do_request(self, *, system_prompt, user_message, model,\n                    temperature, max_tokens):", stream_method)
            master_path.write_text(content, encoding="utf-8")
            print("[+] master.py: добавлен narrate_stream")

    # 3. orchestrator.py: Добавляем process_turn_stream
    orch_path = ROOT / "services" / "orchestrator.py"
    if orch_path.exists():
        content = orch_path.read_text(encoding="utf-8")
        
        stream_orch = r'''
    def process_turn_stream(self, player_input: str, state: Any,
                            *, history: Optional[list] = None,
                            max_tokens: int = 700, meta_out: dict = None):
        """Генератор хода для стриминга."""
        if meta_out is None:
            meta_out = {}
            
        mod = self.moderator.check(player_input)
        meta_out['moderation'] = mod
        if mod.verdict != "ALLOW":
            redirect = (mod.redirect or "").strip() or "Ты возвращаешься к сцене."
            yield ensure_action_variants(redirect)
            return

        command = self.analyst.parse(player_input)
        meta_out['command'] = command
        
        roll = None
        if command.roll_needed:
            skill = command.skill or "Per"
            base = self._lookup_skill(state, skill)
            roll = roll_check(base, difficulty=command.difficulty, reason=skill)
        meta_out['roll'] = roll

        rag_ctx = ""
        rag_sources: list = []
        rag_n = 0
        faction = state.get("faction_id") if isinstance(state, dict) else None
        
        if self.kb is not None:
            enriched = self._enrich_query(player_input, command, state=state)
            try:
                chunks = self.kb.search(enriched, top_k=4, faction=faction) or []
                rag_n = len(chunks)
                if chunks:
                    rag_ctx = self.kb.format_context(enriched, top_k=4, faction=faction)
                    rag_sources = self._extract_sources(chunks)
            except Exception as e:
                print("[orchestrator] RAG ошибка: " + str(e))
        
        meta_out['rag_chunks'] = rag_n
        meta_out['rag_sources'] = rag_sources

        choice_hint = _choice_hint_for(player_input, history or [])
        full_ctx = (rag_ctx or "") + choice_hint

        for chunk in self.master.narrate_stream(
            state, command, roll=roll, history=history or [],
            extra_context=full_ctx, max_tokens=max_tokens
        ):
            yield chunk
'''
        if "def process_turn_stream" not in content:
            # Вставляем перед _enrich_query
            content = content.replace("    @staticmethod\n    def _enrich_query", stream_orch + "\n    @staticmethod\n    def _enrich_query")
            orch_path.write_text(content, encoding="utf-8")
            print("[+] orchestrator.py: добавлен process_turn_stream")

    # 4. game_service.py: Добавляем process_player_action_stream
    gs_path = ROOT / "services" / "game_service.py"
    if gs_path.exists():
        content = gs_path.read_text(encoding="utf-8")
        
        stream_gs = r'''
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
'''
        if "def process_player_action_stream" not in content:
            content += stream_gs
            gs_path.write_text(content, encoding="utf-8")
            print("[+] game_service.py: добавлен process_player_action_stream")

    # 5. game.py: Внедряем стриминг в UI
    game_path = ROOT / "ui" / "screens" / "game.py"
    if game_path.exists():
        content = game_path.read_text(encoding="utf-8")
        
        # Ищем блок обработки хода
        old_turn = r'''        with st.chat_message("assistant"):
            with st.status("⚙️ Дух-машины обрабатывают запрос...",
                           expanded=True) as _status:
                st.write("Анализ действия игрока...")
                try:
                    orch = _get_orch()
                    game_service = GameService(orch)
                    _max_tokens = max_tokens_for(login)
                    clean_text, roll_dict, applied, char, cmd = game_service.process_player_action(
                        login, char_name, prompt, history, _max_tokens
                    )
                    _status.update(label="✔ Ответ получен",
                                   state="complete", expanded=False)
                except Exception as _e:
                    _status.update(
                        label="⚠ Ошибка: " + type(_e).__name__,
                        state="error", expanded=True,
                    )
                    st.error("Мастер не смог обработать действие: " + str(_e))
                    if st.button("🔄 Повторить ход", key="retry_turn"):
                        st.rerun()
                    return'''
        
        new_turn = r'''        with st.chat_message("assistant"):
            with st.status("⚙️ Дух-машины обрабатывают запрос...",
                           expanded=True) as _status:
                st.write("Анализ действия игрока...")
                meta = {}
                try:
                    orch = _get_orch()
                    game_service = GameService(orch)
                    _max_tokens = max_tokens_for(login)
                    
                    # Стриминг текста
                    response_placeholder = st.empty()
                    full_text = ""
                    stream = game_service.process_player_action_stream(
                        login, char_name, prompt, history, _max_tokens, meta
                    )
                    import re
                    for chunk in stream:
                        full_text += chunk
                        # Прячем [STATE] от пользователя во время печати
                        display_text = re.sub(r'\[STATE\].*?(?:\[/STATE\]|$)', '', full_text, flags=re.DOTALL)
                        response_placeholder.markdown(display_text)
                    
                    _status.update(label="✔ Ответ получен",
                                   state="complete", expanded=False)
                except Exception as _e:
                    _status.update(
                        label="⚠ Ошибка: " + type(_e).__name__,
                        state="error", expanded=True,
                    )
                    st.error("Мастер не смог обработать действие: " + str(_e))
                    return
            
            # После стрима забираем данные из meta
            clean_text = meta.get('clean_text', response_text)
            roll_dict = meta.get('roll').to_dict() if meta.get('roll') else None
            char = meta.get('updated_char', char)
            cmd = meta.get('command')
            
            # Добавляем кнопку генерации картинки (PATCH_122)
            if st.button("🎨 Иллюстрация к сцене", key="gen_img_" + str(hash(clean_text))):
                from services.image_service import generate_image
                import random
                st.session_state["_img_seed"] = random.randint(1, 100000)
                # Берем последние 300 символов как промпт
                img_prompt = clean_text[-300:]
                img_url = generate_image(img_prompt)
                st.image(img_url, caption="Сцена", use_container_width=True)'''

        if "process_player_action_stream" not in content:
            if old_turn in content:
                content = content.replace(old_turn, new_turn)
                game_path.write_text(content, encoding="utf-8")
                print("[+] game.py: внедрен стриминг и кнопка иллюстрации")
            else:
                print("[-] game.py: не найден блок для замены. Проверь вручную.")

if __name__ == "__main__":
    apply_patch_122()
    print("=== Готово ===")