import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

def apply_patch_131():
    print("=== PATCH_131: Memory Optimization for Streamlit Cloud ===")

    # 1. Отключаем предзагрузку RAG в app.py
    app_path = ROOT / "app.py"
    if app_path.exists():
        content = app_path.read_text(encoding="utf-8")
        
        old_rag_load = '''    # 3. RAG (самое тяжелое)
    logger.info("Загрузка RAG (ChromaDB + модель)...")
    try:
        get_kb()  # Прогревает кэш
        logger.info("RAG загружен в память.")
    except Exception as e:
        logger.error(f"RAG failed: {e}")'''
        
        new_rag_load = '''    # 3. RAG (ОТКЛЮЧЕНО для экономии памяти на Streamlit Cloud)
    logger.info("Пропуск загрузки RAG (экономия ОЗУ). Используется текстовый fallback.")'''
        
        if old_rag_load in content:
            content = content.replace(old_rag_load, new_rag_load)
            app_path.write_text(content, encoding="utf-8")
            print("[+] app.py: предзагрузка RAG отключена (спасение от OOM)")

    # 2. Убеждаемся, что Orchestrator запускается без RAG в game.py
    game_path = ROOT / "ui" / "screens" / "game.py"
    if game_path.exists():
        content = game_path.read_text(encoding="utf-8")
        
        old_orch = 'st.session_state.orchestrator = Orchestrator(cfg, use_rag=True)'
        new_orch = 'st.session_state.orchestrator = Orchestrator(cfg, use_rag=False)  # PATCH_131: RAG отключен для стабильности'
        
        if old_orch in content:
            content = content.replace(old_orch, new_orch)
            game_path.write_text(content, encoding="utf-8")
            print("[+] game.py: Orchestrator переведен на use_rag=False")

    # 3. Проверяем, что в bot_vk.py тоже отключено (чтобы бот не падал)
    bot_path = ROOT / "bot_vk.py"
    if bot_path.exists():
        content = bot_path.read_text(encoding="utf-8")
        if "Orchestrator(config)" in content:
            content = content.replace("Orchestrator(config)", "Orchestrator(config, use_rag=False)")
            bot_path.write_text(content, encoding="utf-8")
            print("[+] bot_vk.py: RAG отключен для бота")

    print("\n=== Готово ===")

if __name__ == "__main__":
    apply_patch_131()