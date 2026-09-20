# init_db.py
# Проверяет, есть ли chroma_db. Если пусто — запускает build_embeddings.
# Вызывается один раз при старте app.py.

import os
import sys
import subprocess
import streamlit as st


CHROMA_DIR = "chroma_db"
MARKER_FILE = os.path.join(CHROMA_DIR, ".ready")


def _is_db_ready() -> bool:
    """База считается готовой, если есть папка и внутри неё — маркер .ready."""
    if not os.path.isdir(CHROMA_DIR):
        return False
    if not os.path.exists(MARKER_FILE):
        return False
    try:
        files = [f for f in os.listdir(CHROMA_DIR) if f != ".ready"]
    except Exception:
        return False
    return len(files) > 0


def _mark_ready():
    os.makedirs(CHROMA_DIR, exist_ok=True)
    with open(MARKER_FILE, "w", encoding="utf-8") as f:
        f.write("ok")


def ensure_db() -> bool:
    """
    Гарантирует, что chroma_db собран.
    Возвращает True, если база готова. False — если что-то пошло не так.
    """
    if _is_db_ready():
        print("✅ chroma_db уже собран.")
        return True

    print("⚠ chroma_db отсутствует или неполный — запускаю build_embeddings.py")
    with st.spinner("🔄 Первый запуск: собираю векторную базу (30–60 секунд)..."):
        try:
            result = subprocess.run(
                [sys.executable, "build_embeddings.py"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=900,
            )
            if result.returncode == 0:
                _mark_ready()
                st.success("✅ База знаний готова.")
                print("✅ build_embeddings.py завершился успешно.")
                return True
            else:
                err_tail = (result.stderr or result.stdout or "")[-1000:]
                st.error(f"❌ Не удалось собрать базу. Хвост логов:\n{err_tail}")
                print("STDERR:", result.stderr)
                print("STDOUT:", result.stdout)
                return False
        except subprocess.TimeoutExpired:
            st.error("❌ Сборка базы заняла больше 15 минут — прерываю.")
            return False
        except Exception as e:
            st.error(f"❌ Ошибка при сборке базы: {e}")
            return False