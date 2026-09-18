# scraper.py
# Умный парсер + адаптация через GigaChat.
# 4 уровня поиска: прямые URL → fallback → Wayback → автопоиск.
# Адаптация: GigaChat переписывает сырой лор в формат Rogue Trader.

import os
import re
import time
import shutil
import argparse
from datetime import datetime
from urllib.parse import urlparse, quote_plus

import streamlit as st

from curl_cffi import requests as curl_requests
from bs4 import BeautifulSoup

from gigachat import GigaChat
from gigachat.models import Chat, Messages, MessagesRole

from sources_config import SOURCES


# ============================================================
# НАСТРОЙКИ
# ============================================================
DATA_DIR = "data"
BACKUP_DIR = "data_backup"
REQUEST_TIMEOUT = 40
POLITE_DELAY = 1.0
MAX_RETRIES = 2
IMPERSONATE = "chrome124"

# GigaChat
try:
    API_KEY = st.secrets["GIGACHAT_API_KEY"]
except Exception:
    API_KEY = "MDFhMDk2NGMtZGQ0Yi03NGJiLTkzNWEtODgzMWEwNjZjZDYzOjBkNDViZDZmLTYxYzQtNGYyNC1hYzFlLTczZGY5OWI5MDZiMw=="

GIGA_MODEL = "GigaChat-2-Pro"
ADAPTATION_PROMPT_PATH = "prompts/adaptation.txt"
ADAPT_TIMEOUT = 90       # секунд на один запрос
MAX_ADAPT_CHARS = 6000   # длинные тексты режем на куски
ADAPT_RETRIES = 2        # сколько раз повторять упавший чанк

MEDIAWIKI_DOMAINS = ["fandom.com", "lexicanum.com"]


# ============================================================
# ЗАГРУЗКА
# ============================================================
def fetch_via_mediawiki(page_url: str) -> str:
    parsed = urlparse(page_url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    title = parsed.path.replace("/wiki/", "").replace("_", " ")

    api_url = f"{base}/api.php"
    params = {
        "action": "parse", "page": title, "prop": "text",
        "format": "json", "formatversion": "2", "disablelimitreport": "1",
    }
    resp = curl_requests.get(
        api_url, params=params, impersonate=IMPERSONATE, timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()

    if "error" in data:
        raise RuntimeError(f"MediaWiki API error: {data['error'].get('info', 'unknown')}")

    html = data.get("parse", {}).get("text", "")
    if not html:
        raise RuntimeError("MediaWiki API вернул пустой HTML.")
    return html


def search_mediawiki(query: str, wiki_base: str) -> list:
    api_url = f"{wiki_base}/api.php"
    params = {
        "action": "query", "list": "search", "srsearch": query,
        "srlimit": 5, "format": "json", "formatversion": "2",
    }
    try:
        resp = curl_requests.get(
            api_url, params=params, impersonate=IMPERSONATE, timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return []

    results = []
    for item in data.get("query", {}).get("search", []):
        title = item.get("title", "").replace(" ", "_")
        if title:
            results.append(f"{wiki_base}/wiki/{title}")
    return results


def search_duckduckgo(query: str, max_results: int = 5) -> list:
    url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
    try:
        resp = curl_requests.get(url, impersonate=IMPERSONATE, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
    except Exception:
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    results = []
    for a in soup.find_all("a", {"class": "result__a"}, href=True):
        href = a["href"]
        if "uddg=" in href:
            from urllib.parse import parse_qs, unquote
            try:
                qs = parse_qs(urlparse(href).query)
                href = unquote(qs.get("uddg", [""])[0])
            except Exception:
                continue
        if href.startswith("http"):
            results.append(href)
            if len(results) >= max_results:
                break
    return results


def fetch_via_html(url: str) -> str:
    last_err = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            resp = curl_requests.get(
                url, impersonate=IMPERSONATE, timeout=REQUEST_TIMEOUT,
            )
            resp.raise_for_status()
            return resp.text
        except Exception as e:
            last_err = e
            if attempt < MAX_RETRIES:
                time.sleep(2)
    raise RuntimeError(f"Не удалось загрузить {url}: {last_err}")


# ============================================================
# ЧИСТИЛЬЩИКИ
# ============================================================
def _clean_common(soup):
    for tag in soup(["script", "style", "nav", "footer", "header", "aside",
                     "form", "noscript", "iframe", "svg", "table"]):
        tag.decompose()
    return soup


def _extract_text(main):
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
    return re.sub(r"\n{3,}", "\n\n", result).strip()


def clean_lexicanum(html):
    soup = _clean_common(BeautifulSoup(html, "html.parser"))
    main = soup.find("div", {"class": "mw-parser-output"}) or soup
    return _extract_text(main)


def clean_fandom(html):
    soup = _clean_common(BeautifulSoup(html, "html.parser"))
    main = soup.find("div", {"class": "mw-parser-output"}) or soup
    return _extract_text(main)


def clean_generic(html):
    soup = _clean_common(BeautifulSoup(html, "html.parser"))
    main = soup.find("main") or soup.find("article") or soup.body or soup
    return _extract_text(main)


CLEANERS = {
    "lexicanum": clean_lexicanum,
    "fandom": clean_fandom,
    "generic": clean_generic,
}


# ============================================================
# АДАПТАЦИЯ ЧЕРЕЗ GIGACHAT
# ============================================================
_giga_client = None
_adaptation_prompt = None


def get_giga():
    global _giga_client
    if _giga_client is None:
        _giga_client = GigaChat(
            credentials=API_KEY,
            verify_ssl_certs=False,
            scope="GIGACHAT_API_PERS",
            model=GIGA_MODEL,
        )
    return _giga_client


def get_adaptation_prompt():
    global _adaptation_prompt
    if _adaptation_prompt is None:
        with open(ADAPTATION_PROMPT_PATH, encoding="utf-8") as f:
            _adaptation_prompt = f.read()
    return _adaptation_prompt


def _adapt_chunk(giga, prompt: str):
    """Один запрос к GigaChat. Возвращает текст или None."""
    try:
        resp = giga.chat(Chat(messages=[
            Messages(role=MessagesRole.USER, content=prompt),
        ]))
        text = resp.choices[0].message.content.strip()
        return text if text else None
    except Exception as e:
        print(f"      запрос упал: {e}")
        return None


def adapt_with_llm(raw_text: str, source_url: str) -> str:
    """
    Отправляет сырой текст в GigaChat, просит адаптировать под Rogue Trader.
    Если текст длинный — режет на куски и адаптирует по частям.
    Упавшие чанки повторяет (до ADAPT_RETRIES раз). Если все retry упали —
    фоллбек: сохранить сырой кусок (но с пометкой).
    """
    giga = get_giga()
    template = get_adaptation_prompt()

    # Разбиваем на куски
    chunks = []
    if len(raw_text) <= MAX_ADAPT_CHARS:
        chunks = [raw_text]
    else:
        current = ""
        for para in raw_text.split("\n\n"):
            if len(current) + len(para) + 2 < MAX_ADAPT_CHARS:
                current = (current + "\n\n" + para).strip()
            else:
                if current:
                    chunks.append(current)
                current = para
        if current:
            chunks.append(current)

    adapted_parts = []
    failed_chunks = 0

    for i, chunk in enumerate(chunks, 1):
        print(f"   🤖 Адаптация чанка {i}/{len(chunks)} ({len(chunk)} симв.)...")

        prompt = template.replace("{raw_text}", chunk)
        adapted = None

        # Первая попытка + retry
        for attempt in range(1, ADAPT_RETRIES + 1):
            if attempt > 1:
                print(f"      retry #{attempt}...")
                time.sleep(3)
            adapted = _adapt_chunk(giga, prompt)
            if adapted:
                break

        if adapted:
            adapted_parts.append(adapted)
        else:
            print(f"   ⚠ Чанк {i} не поддался после {ADAPT_RETRIES} попыток.")
            adapted_parts.append(
                f"[НЕАДАПТИРОВАННЫЙ ФРАГМЕНТ {i}]\n{chunk}"
            )
            failed_chunks += 1

        time.sleep(1.5)  # пауза между запросами к GigaChat

    if not adapted_parts:
        return None

    if failed_chunks:
        print(f"   ⚠ Итого неадаптированных чанков: {failed_chunks}/{len(chunks)}")

    return "\n\n".join(adapted_parts)


# ============================================================
# УТИЛИТЫ
# ============================================================
def backup_existing(path):
    if not os.path.exists(path):
        return
    today = datetime.now().strftime("%Y-%m-%d")
    rel = os.path.relpath(path, DATA_DIR)
    backup_path = os.path.join(BACKUP_DIR, today, rel)
    os.makedirs(os.path.dirname(backup_path), exist_ok=True)
    shutil.copy2(path, backup_path)


def try_fetch(url: str, api_type: str, source_type: str):
    domain = urlparse(url).netloc.lower()

    if "fandom.com" in domain:
        actual_api, actual_cleaner = "mediawiki", "fandom"
    elif "lexicanum.com" in domain:
        actual_api, actual_cleaner = "mediawiki", "lexicanum"
    elif "web.archive.org" in domain:
        actual_api, actual_cleaner = "html", source_type
    else:
        actual_api, actual_cleaner = api_type, source_type

    try:
        if actual_api == "mediawiki":
            html = fetch_via_mediawiki(url)
        else:
            html = fetch_via_html(url)
        return html, actual_cleaner
    except Exception as e:
        return None, str(e)


def save_text(url: str, text: str, folder: str, name: str,
              adapted: bool = False) -> bool:
    target_dir = os.path.join(DATA_DIR, folder)
    os.makedirs(target_dir, exist_ok=True)
    target_path = os.path.join(target_dir, name + ".txt")

    backup_existing(target_path)

    header_adapted = "=== АДАПТИРОВАНО ДЛЯ ROGUE TRADER ===" if adapted else "=== СЫРОЙ ЛОР ==="

    with open(target_path, "w", encoding="utf-8") as f:
        f.write(f"{header_adapted}\n")
        f.write(f"=== ИСТОЧНИК: {url} ===\n")
        f.write(f"=== ОБНОВЛЕНО: {datetime.now().strftime('%Y-%m-%d %H:%M')} ===\n\n")
        f.write(text)

    print(f"   ✅ {target_path} ({len(text)} симв., {'адаптировано' if adapted else 'сырой'})")
    return True


# ============================================================
# СОХРАНЕНИЕ С АДАПТАЦИЕЙ
# ============================================================
def try_save(url: str, api_type: str, source_type: str, folder: str, name: str,
             adapt: bool = True, min_len: int = 200) -> bool:
    html, cleaner_result = try_fetch(url, api_type, source_type)
    if html is None:
        print(f"   ❌ {cleaner_result}")
        return False

    cleaner = CLEANERS.get(cleaner_result, clean_generic)
    raw_text = cleaner(html)
    if len(raw_text) < min_len:
        print(f"   ⚠ Мало текста ({len(raw_text)}).")
        return False

    print(f"   📄 Скачано {len(raw_text)} симв. сырого текста.")

    if adapt:
        adapted = adapt_with_llm(raw_text, url)
        if adapted:
            return save_text(url, adapted, folder, name, adapted=True)
        else:
            print(f"   ⚠ Адаптация не удалась, сохраняю сырой текст.")
            return save_text(url, raw_text, folder, name, adapted=False)
    else:
        return save_text(url, raw_text, folder, name, adapted=False)


# ============================================================
# ПОИСК ПО САЙТАМ
# ============================================================
def search_sources(query: str) -> list:
    results = []
    results.extend(search_mediawiki(query, "https://warhammer40k.fandom.com"))
    results.extend(search_mediawiki(query, "https://warhammer40k.fandom.com/ru"))
    results.extend(search_duckduckgo(f"Warhammer 40K {query}"))
    return results


# ============================================================
# ОБРАБОТКА ИСТОЧНИКА
# ============================================================
def process_source(faction_key, source_key, config):
    api_type = config.get("api", "html")
    source_type = config.get("source", "generic")
    folder = config.get("folder", faction_key)
    name = config.get("name", source_key)
    urls = config.get("urls", [])
    fallbacks = config.get("fallback_urls", [])
    waybacks = config.get("wayback_urls", [])
    search_queries = config.get("search_queries", [])
    description = config.get("description", "")
    adapt = config.get("adapt", True)

    print(f"\n🔹 [{faction_key}.{source_key}] {description} [adapt={adapt}]")

    # ---- Уровень 1-3: прямые URL ----
    for idx, url in enumerate(urls + fallbacks + waybacks):
        label = "основной" if idx == 0 else f"fallback #{idx}"
        print(f"   📥 [{label}] {url}")

        if try_save(url, api_type, source_type, folder, name, adapt=adapt):
            return True
        time.sleep(POLITE_DELAY)

    # ---- Уровень 4: автопоиск ----
    print(f"   🔍 Прямые URL не сработали, ищу автоматически...")

    if not search_queries:
        search_queries = [f"{faction_key} {name.replace('_', ' ')}"]

    for q in search_queries:
        print(f"   🔎 Запрос: '{q}'")
        candidates = search_sources(q)
        if not candidates:
            print(f"   ⚠ Ничего не найдено.")
            continue

        for candidate in candidates[:5]:
            print(f"   📥 [search] {candidate}")
            if try_save(candidate, "mediawiki", "fandom", folder, name,
                        adapt=adapt, min_len=500):
                return True
            time.sleep(0.5)

    print(f"   💀 Не удалось найти информацию для [{folder}/{name}].")
    return False


# ============================================================
# CLI
# ============================================================
def list_sources():
    print("=" * 60)
    print("ДОСТУПНЫЕ ИСТОЧНИКИ")
    print("=" * 60)
    for faction, sources in SOURCES.items():
        print(f"\n📁 {faction}")
        for key, cfg in sources.items():
            desc = cfg.get("description", "")
            adapt = cfg.get("adapt", True)
            print(f"   {faction}.{key:<26} [adapt={adapt}] {desc}")


def run_faction(faction_key):
    if faction_key not in SOURCES:
        print(f"❌ Фракция '{faction_key}' не найдена.")
        return
    print("=" * 60)
    print(f"ПАРСИНГ ФРАКЦИИ: {faction_key}")
    print("=" * 60)
    for source_key, config in SOURCES[faction_key].items():
        process_source(faction_key, source_key, config)


def run_one(faction_key, source_key, force_adapt=None):
    if faction_key not in SOURCES or source_key not in SOURCES[faction_key]:
        print(f"❌ Не найдено: {faction_key}.{source_key}")
        return
    config = dict(SOURCES[faction_key][source_key])
    if force_adapt is not None:
        config["adapt"] = force_adapt
    process_source(faction_key, source_key, config)


def run_all():
    print("=" * 60)
    print("ПАРСИНГ ВСЕХ ИСТОЧНИКОВ")
    print("=" * 60)
    ok, fail = 0, 0
    for faction_key, sources in SOURCES.items():
        print(f"\n{'=' * 60}\nФРАКЦИЯ: {faction_key}\n{'=' * 60}")
        for source_key, config in sources.items():
            if process_source(faction_key, source_key, config):
                ok += 1
            else:
                fail += 1
    print(f"\n{'=' * 60}")
    print(f"ИТОГО: успешно — {ok}, с ошибками — {fail}")
    print(f"{'=' * 60}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--faction")
    parser.add_argument("--key")
    parser.add_argument("--adapt", action="store_true",
                        help="Принудительно адаптировать через GigaChat")
    parser.add_argument("--no-adapt", action="store_true",
                        help="Не адаптировать, сохранять сырой текст")
    args = parser.parse_args()

    if args.list:
        list_sources()
        return

    force_adapt = None
    if args.adapt:
        force_adapt = True
    elif args.no_adapt:
        force_adapt = False

    if args.all:
        if force_adapt is not None:
            for faction_key in SOURCES:
                for source_key in SOURCES[faction_key]:
                    SOURCES[faction_key][source_key]["adapt"] = force_adapt
        run_all()
    elif args.faction:
        run_faction(args.faction)
    elif args.key:
        if "." not in args.key:
            print("❌ Формат --key: <фракция>.<источник>")
            return
        f, s = args.key.split(".", 1)
        run_one(f, s, force_adapt=force_adapt)
    else:
        parser.print_help()
        return

    print("\nТеперь запусти: python build_embeddings.py")


if __name__ == "__main__":
    main()