import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

def apply_patch_130():
    print("=== PATCH_130: Global Caching & Startup Loading ===")

    # ===== 1. УБИРАЕМ init_db() ИЗ ВСЕХ ВЫЗОВОВ =====
    # База должна инициализироваться ОДИН раз в app.py, а не при каждом клике
    db_users = [
        ROOT / "persistence" / "characters.py",
        ROOT / "persistence" / "chats.py",
        ROOT / "persistence" / "accounts.py",
        ROOT / "persistence" / "settings.py",
        ROOT / "services" / "settings_game.py",
        ROOT / "services" / "world_memory.py"
    ]
    
    for f in db_users:
        if f.exists():
            content = f.read_text(encoding="utf-8")
            # Заменяем "init_db()" на комментарий (безопасно)
            if "init_db()" in content:
                content = content.replace("init_db()", "# init_db()  # PATCH_130: moved to app startup")
                f.write_text(content, encoding="utf-8")
                print(f"[+] {f.name}: убрана инициализация БД при каждом вызове")

    # ===== 2. ГЛОБАЛЬНАЯ ЗАГРУЗКА В app.py =====
    app_path = ROOT / "app.py"
    if app_path.exists():
        content = app_path.read_text(encoding="utf-8")
        
        old_init = '''@st.cache_resource
def _bootstrap_init():
    from scripts.bootstrap import init_project
    from persistence.db import init_db
    init_project()
    init_db()'''
        
        new_init = '''@st.cache_resource(show_spinner=False)
def _bootstrap_init():
    from scripts.bootstrap import init_project
    from persistence.db import init_db
    from services.rag import get_kb
    from core.logger import get_logger
    
    logger = get_logger(__name__)
    logger.info("Инициализация проекта (1 раз)...")
    
    # 1. Распаковка архивов
    init_project()
    
    # 2. База данных
    init_db()
    
    # 3. RAG (самое тяжелое)
    logger.info("Загрузка RAG (ChromaDB + модель)...")
    try:
        get_kb()  # Прогревает кэш
        logger.info("RAG загружен в память.")
    except Exception as e:
        logger.error(f"RAG failed: {e}")'''
        
        if old_init in content and "show_spinner=False" not in content:
            content = content.replace(old_init, new_init)
            app_path.write_text(content, encoding="utf-8")
            print("[+] app.py: добавлена предзагрузка RAG (теперь клики будут быстрыми)")
        else:
            print("[!] app.py: блок инициализации не найден или уже обновлен")

    # ===== 3. КЭШИРОВАНИЕ ПОДКЛЮЧЕНИЯ К БД =====
    db_path = ROOT / "persistence" / "db.py"
    if db_path.exists():
        content = db_path.read_text(encoding="utf-8")
        # Делаем get_conn кэшированным (безопасно для SQLite)
        if "@st.cache_resource" not in content:
            old_conn = "def get_conn():"
            new_conn = "import streamlit as st\n\n@st.cache_resource\ndef get_conn():"
            content = content.replace(old_conn, new_conn)
            db_path.write_text(content, encoding="utf-8")
            print("[+] db.py: подключение к базе закэшировано")

    print("\n=== Готово ===")

if __name__ == "__main__":
    apply_patch_130()