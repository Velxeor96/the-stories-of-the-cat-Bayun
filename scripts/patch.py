import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

def apply_patch_133():
    print("=== PATCH_133: Lightweight RAG (text fallback) ===")

    # 1. game.py — возвращаем use_rag=True (будет работать через fallback)
    game_path = ROOT / "ui" / "screens" / "game.py"
    if game_path.exists():
        content = game_path.read_text(encoding="utf-8")
        old = 'Orchestrator(cfg, use_rag=False)'
        new = 'Orchestrator(cfg, use_rag=True)  # PATCH_133: легкий текстовый RAG'
        if old in content:
            content = content.replace(old, new)
            game_path.write_text(content, encoding="utf-8")
            print("[+] game.py: use_rag=True (текстовый fallback)")

    # 2. bot_vk.py — то же
    bot_path = ROOT / "bot_vk.py"
    if bot_path.exists():
        content = bot_path.read_text(encoding="utf-8")
        old = 'Orchestrator(config, use_rag=False)'
        new = 'Orchestrator(config, use_rag=True)'
        if old in content:
            content = content.replace(old, new)
            bot_path.write_text(content, encoding="utf-8")
            print("[+] bot_vk.py: use_rag=True")

    # 3. rag.py — принудительно только fallback (без попыток лезть в chromadb)
    rag_path = ROOT / "services" / "rag.py"
    if rag_path.exists():
        content = rag_path.read_text(encoding="utf-8")
        # Отключаем попытку vector-init полностью — сразу fallback
        if "def _try_init_vector_mode" in content:
            old_block = '''    def _try_init_vector_mode(self) -> None:
        try:
            if chromadb is None:
                return'''
            new_block = '''    def _try_init_vector_mode(self) -> None:
        # PATCH_133: принудительно fallback (экономим память)
        return
        try:
            if chromadb is None:
                return'''
            if old_block in content:
                content = content.replace(old_block, new_block)
                rag_path.write_text(content, encoding="utf-8")
                print("[+] rag.py: vector-режим принудительно отключен, работает text fallback")

    # 4. Проверяем, что _load_fallback_chunks работает
    if rag_path.exists():
        content = rag_path.read_text(encoding="utf-8")
        if "_load_fallback_chunks" not in content:
            print("[-] ВНИМАНИЕ: fallback-функция не найдена! RAG не будет работать вообще.")
        else:
            print("[+] rag.py: text fallback на месте (грузит data/*/*.txt в память)")

    print("\n=== Готово ===")
    print("Легкий RAG: ~2 МБ памяти, поиск по ключевым словам без torch/chromadb")

if __name__ == "__main__":
    apply_patch_133()