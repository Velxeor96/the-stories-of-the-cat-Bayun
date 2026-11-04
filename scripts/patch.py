from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def update_release():
    print("=== Подготовка релиза 2.2.0 ===")
    
    # Обновляем VERSION
    version_path = ROOT / "VERSION"
    version_path.write_text("2.2.0\n", encoding="utf-8")
    print("[+] VERSION обновлен до 2.2.0")
    
    # Обновляем CHANGELOG.md
    changelog_path = ROOT / "CHANGELOG.md"
    old_content = ""
    if changelog_path.exists():
        old_content = changelog_path.read_text(encoding="utf-8")
        
    new_entry = """# 2.2.0 — Xenos DLC & Mobile Architecture (04.11.2026)

## 🚀 Новые фракции (DLC)
- Активированы **Эльдары**, **Тау**, **Некроны** и **Тираниды**.
- Созданы файлы-фасады (`factions/*.json`) и песочные сюжетные профили (`story/*.json`).
- Обновлены пути в `services/necrons.py` и `services/tyranids.py` (убран `_inactive`).
- В `wizard.py` и `character_creation.py` добавлены 4 новые расы для выбора.

## 🏗 Архитектура, UI и Мобильная версия
- **PWA:** Добавлен `static/manifest.json` и мобильный CSS в `ui/theme.py` (кнопки на всю ширину, адаптивные отступы).
- **VK-бот:** Создан каркас `bot_vk.py` с интеграцией `Orchestrator` и SQLite.
- **Песочница:** Переписаны промпты в `master.py`. Сюжетные профили теперь передаются как «фоновые слухи», ИИ больше не ведет игрока по рельсам.
- **UI Capabilities:** В `manifest.json` добавлена секция `"capabilities"`. В `app.py` внедрена фильтрация экранов (если нет `combat`, экран боя скрывается).

## 📋 Тесты
- `pytest tests/` -> **50 passed**.

---

"""
    changelog_path.write_text(new_entry + old_content, encoding="utf-8")
    print("[+] CHANGELOG.md обновлен (добавлена запись 2.2.0)")

if __name__ == "__main__":
    update_release()