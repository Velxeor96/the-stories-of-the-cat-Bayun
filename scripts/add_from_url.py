# add_from_url.py
# Скачивает страницу по URL, чистит HTML, сохраняет в data/imported/.
# После этого можно запустить build_embeddings.py — новые чанки добавятся в базу.
#
# Использование:
#   python add_from_url.py <url> [--folder=<папка>] [--name=<имя_файла>]
#
# Примеры:
#   python add_from_url.py https://wh40k.lexicanum.com/wiki/Eldar
#   python add_from_url.py https://example.com/page --folder=eldar --name=my_topic

import os
import re
import sys
import argparse
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup


IMPORT_DIR = "data/imported"


def slugify(text: str, max_len: int = 60) -> str:
    """Преобразует строку в безопасное имя файла."""
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE)
    text = re.sub(r"[\s_-]+", "_", text).strip("_")
    return text[:max_len] or "page"


def fetch_html(url: str) -> str:
    """Скачивает HTML страницы с User-Agent, чтобы не блокировали."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0 Safari/537.36"
        )
    }
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.text


def clean_html(html: str) -> str:
    """
    Убирает скрипты, стили, навигацию, футеры.
    Оставляет только основной текст.
    """
    soup = BeautifulSoup(html, "html.parser")

    # Удаляем мусор
    for tag in soup(["script", "style", "nav", "footer", "header", "aside",
                     "form", "noscript", "iframe", "svg"]):
        tag.decompose()

    # Пытаемся найти основной контент
    main = (
        soup.find("main")
        or soup.find("article")
        or soup.find("div", {"id": "content"})
        or soup.find("div", {"class": "content"})
        or soup.find("div", {"id": "mw-content-text"})  # MediaWiki (Lexicanum)
        or soup.body
        or soup
    )

    # Достаём текст абзацев, списков, заголовков
    lines = []
    for el in main.find_all(["h1", "h2", "h3", "h4", "p", "li", "blockquote"]):
        text = el.get_text(" ", strip=True)
        text = re.sub(r"\s+", " ", text)
        if len(text) < 20:
            continue

        if el.name in ("h1", "h2", "h3", "h4"):
            lines.append(f"\n=== {text} ===\n")
        elif el.name == "li":
            lines.append(f"- {text}")
        elif el.name == "blockquote":
            lines.append(f"> {text}")
        else:
            lines.append(text)

    result = "\n\n".join(lines)
    result = re.sub(r"\n{3,}", "\n\n", result)
    return result.strip()


def main():
    parser = argparse.ArgumentParser(description="Скачать страницу и добавить в базу")
    parser.add_argument("url", help="URL страницы")
    parser.add_argument("--folder", default="imported",
                        help="Подпапка в data/ (например, eldar, orks)")
    parser.add_argument("--name", default=None,
                        help="Имя файла без .txt (по умолчанию — из URL)")
    args = parser.parse_args()

    url = args.url
    print(f"📥 Скачиваем: {url}")

    try:
        html = fetch_html(url)
    except Exception as e:
        print(f"❌ Ошибка загрузки: {e}")
        return 1

    print("🧹 Чистим HTML...")
    text = clean_html(html)

    if len(text) < 200:
        print(f"⚠ Текста мало ({len(text)} симв.). Возможно, страница защищена.")
        print("   Первые 300 символов:")
        print(text[:300])

    # Определяем имя файла
    if args.name:
        fname = slugify(args.name) + ".txt"
    else:
        path = urlparse(url).path
        last = path.rstrip("/").split("/")[-1] or "page"
        fname = slugify(last) + ".txt"

    # Формируем путь
    folder = args.folder.strip("/")
    target_dir = os.path.join("data", folder)
    os.makedirs(target_dir, exist_ok=True)
    target_path = os.path.join(target_dir, fname)

    # Пишем
    with open(target_path, "w", encoding="utf-8") as f:
        f.write(f"=== ИСТОЧНИК: {url} ===\n\n")
        f.write(text)

    print(f"✅ Сохранено: {target_path}")
    print(f"   Символов: {len(text)}")
    print()
    print("Теперь запусти: python build_embeddings.py")
    print("(скрипт добавит только НОВЫЕ чанки, старые не тронет)")

    return 0


if __name__ == "__main__":
    sys.exit(main())