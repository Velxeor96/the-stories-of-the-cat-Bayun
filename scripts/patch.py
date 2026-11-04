from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def update_release():
    print("=== Подготовка релиза 2.2.1 (Hotfix) ===")
    
    # Обновляем VERSION
    (ROOT / "VERSION").write_text("2.2.1\n", encoding="utf-8")
    print("[+] VERSION обновлен до 2.2.1")
    
    # Обновляем CHANGELOG.md
    changelog_path = ROOT / "CHANGELOG.md"
    old_content = changelog_path.read_text(encoding="utf-8") if changelog_path.exists() else ""
        
    new_entry = """# 2.2.1 — System Stability Hotfix (04.11.2026)

## 🛠 Исправления после фидбека тестеров
- **Кэширование (PATCH_119-120):** Внедрен `@st.cache_resource` для `init_project()` и `init_db()`. Устранены задержки 3-7 секунд при переключении экранов.
- **Защита от вылетов (PATCH_119):** В `ui/screens/game.py` и `services/game_service.py` добавлены `try/except`. Если Мастер (GigaChat) падает или RAG выдает ошибку, игрок видит понятное сообщение и кнопку «Попробовать снова», а не красный экран.
- **Локализация (PATCH_119):** В `ui/screens/wizard.py` добавлена функция `_safe_subname`. Теперь Инквизиция и другие субфракции переводятся на русский язык автоматически, даже если их нет в словаре.

## 📋 Тесты
- `pytest tests/` -> **50 passed**.

---

"""
    changelog_path.write_text(new_entry + old_content, encoding="utf-8")
    print("[+] CHANGELOG.md обновлен (добавлена запись 2.2.1)")

if __name__ == "__main__":
    update_release()