# SPLIT_RULEBOOK_V3 — разбор .docx, fallback для утерянных глав
from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

from docx import Document
from docx.document import Document as _Document
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.table import _Cell, Table
from docx.text.paragraph import Paragraph

TAG = "SPLIT_RULEBOOK_V3"
ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

BOOK_CANDIDATES = [
    ROOT / "OKP_Rogue_Trader_rus_v1_23_clean_3.docx",
    ROOT / "OKP_Rogue_trader_rus_v1_23_clean_3.docx",
    ROOT / "data" / "_source" / "OKP_Rogue_Trader_rus_v1_23_clean_3.docx",
    ROOT / "OKP_Rogue_Trader_rus_v1_23_clean_3.txt",
]

CHAPTER_HEADING_RE = re.compile(
    r"^\s*Глава\s+([IVX]+)\s*[.:]\s*(.+?)\s*$",
    re.IGNORECASE,
)
CHAP_IN_TEXT_RE_TEMPLATE = r"Глава\s+{roman}\b"
CHAP_TITLE_RE_TEMPLATE = r"Глава\s+{roman}[.:]?\s*(.+)$"

ROMAN_ORDER = ["I","II","III","IV","V","VI","VII","VIII","IX",
               "X","XI","XII","XIII","XIV","XV"]

CHAPTER_MAP = {
    "I":    ("general",  "__CHARACTER__"),
    "II":   ("general",  "10_careers.txt"),
    "III":  ("general",  "04_skills.txt"),
    "IV":   ("general",  "05_talents.txt"),
    "V":    ("general",  "__ARMORY__"),
    "VI":   ("general",  "08_warp_psy.txt"),
    "VII":  ("general",  "08a_navigator.txt"),
    "VIII": ("general",  "09_space_combat.txt"),
    "IX":   ("general",  "__GAMEPLAY__"),
    "X":    ("general",  "11_gm.txt"),
    "XI":   ("imperium", "lore.txt"),
    "XII":  ("general",  "12_rogue_traders.txt"),
    "XIII": ("general",  "13_koronus.txt"),
    "XIV":  ("general",  "14_adversaries.txt"),
    "XV":   ("general",  "15_adventure_maw.txt"),
}

MARKER_TEMPLATE = (
    "\n\n================================================================\n"
    "ИСТОЧНИК: Rogue Trader Core Rulebook (OKP_RTR v1.23)\n"
    "РАЗДЕЛ: {title}\n"
    "MARKER: {tag}::{key}\n"
    "================================================================\n\n"
)

MAW_HEADER = (
    "# ПРИМЕР ПРИКЛЮЧЕНИЯ\n"
    "# Использовать при необходимости при игре за Империум.\n"
    "# Это не каноничные правила, а вводное приключение из Core Rulebook.\n\n"
)

DAMAGE_PHRASE = "Фрагмент текста повреждён при конвертации PDF"
DAMAGE_MARKER = "[ПОВРЕЖДЕНО ПРИ КОНВЕРТАЦИИ — нужен оригинал]"


def find_book() -> Path:
    for p in BOOK_CANDIDATES:
        if p.exists():
            return p
    print("[ERROR] Книга не найдена. Искал:")
    for p in BOOK_CANDIDATES:
        print("   ", p)
    sys.exit(1)


def iter_block_items(parent):
    if isinstance(parent, _Document):
        parent_elm = parent.element.body
    elif isinstance(parent, _Cell):
        parent_elm = parent._tc
    else:
        raise ValueError("bad parent")
    for child in parent_elm.iterchildren():
        if isinstance(child, CT_P):
            yield Paragraph(child, parent)
        elif isinstance(child, CT_Tbl):
            yield Table(child, parent)


def render_paragraph(p: Paragraph) -> str:
    text = p.text.strip()
    if not text:
        return ""
    text = text.replace(DAMAGE_PHRASE, DAMAGE_MARKER)
    style = p.style.name if p.style else ""
    if style.startswith("Heading "):
        try:
            level = int(style.split(" ")[1])
        except Exception:
            level = 2
        return "#" * max(1, min(level, 6)) + " " + text
    if style == "Title":
        return "# " + text
    if style == "Caption":
        return "> " + text
    if style == "Bullet":
        return "- " + text
    return text


def render_table(table: Table) -> str:
    rows = []
    for row in table.rows:
        cells = []
        for c in row.cells:
            cell_text = c.text.strip().replace("\n", " ").replace("|", "/")
            cells.append(cell_text)
        rows.append("| " + " | ".join(cells) + " |")
    return "\n".join(rows)


def blocks_to_text(blocks) -> str:
    parts = []
    for b in blocks:
        if isinstance(b, Paragraph):
            s = render_paragraph(b)
            if s:
                parts.append(s)
        elif isinstance(b, Table):
            t = render_table(b)
            if t:
                parts.append(t)
    return "\n\n".join(parts)


def _collect_heading1_chapters(blocks):
    chapter_starts = []
    for i, b in enumerate(blocks):
        if not isinstance(b, Paragraph):
            continue
        style = b.style.name if b.style else ""
        if style != "Heading 1":
            continue
        m = CHAPTER_HEADING_RE.match(b.text)
        if m:
            roman = m.group(1).upper()
            title = m.group(2).strip()
            chapter_starts.append([i, roman, title])
    return chapter_starts


def _find_missing_chapters(blocks, chapter_starts):
    found_romans = {c[1] for c in chapter_starts}
    missing = [r for r in ROMAN_ORDER if r not in found_romans]
    if not missing:
        return []
    result = []
    for miss in missing:
        idx_in_order = ROMAN_ORDER.index(miss)
        prev_pos = 0
        for j in range(idx_in_order - 1, -1, -1):
            for c in chapter_starts:
                if c[1] == ROMAN_ORDER[j]:
                    prev_pos = c[0]
                    break
            if prev_pos > 0:
                break
        next_pos = len(blocks)
        for j in range(idx_in_order + 1, len(ROMAN_ORDER)):
            for c in chapter_starts:
                if c[1] == ROMAN_ORDER[j]:
                    next_pos = c[0]
                    break
            if next_pos < len(blocks):
                break
        pat = re.compile(
            CHAP_IN_TEXT_RE_TEMPLATE.format(roman=miss),
            re.IGNORECASE,
        )
        title_pat = re.compile(
            CHAP_TITLE_RE_TEMPLATE.format(roman=miss),
            re.IGNORECASE,
        )
        found = False
        for i in range(prev_pos + 1, next_pos):
            b = blocks[i]
            if not isinstance(b, Paragraph):
                continue
            if not pat.search(b.text):
                continue
            m2 = title_pat.search(b.text)
            title = m2.group(1).strip() if m2 else miss
            result.append([i, miss, title])
            found = True
            break
        if not found:
            print("[warn] не нашёл Главу " + miss +
                  " между блоками " + str(prev_pos) + ".." + str(next_pos))
    return result


def collect_chapters(doc):
    blocks = list(iter_block_items(doc))
    chapter_starts = _collect_heading1_chapters(blocks)
    extra = _find_missing_chapters(blocks, chapter_starts)
    for c in extra:
        print("[info] добавил утерянную главу:", c[1], "->", c[2][:50])
    chapter_starts.extend(extra)
    chapter_starts.sort(key=lambda x: x[0])

    if not chapter_starts:
        return [("intro", "Вступление", blocks)]

    result = []
    if chapter_starts[0][0] > 0:
        result.append(("intro", "Вступление", blocks[:chapter_starts[0][0]]))
    for idx, (start_i, roman, title) in enumerate(chapter_starts):
        end_i = chapter_starts[idx + 1][0] if idx + 1 < len(chapter_starts) else len(blocks)
        result.append((roman, title, blocks[start_i:end_i]))
    return result


def split_character(body: str):
    pat_e2 = re.compile(r"^#+\s*Этап\s*2\s*[.:]?\s*Путь\s+Происхождения",
                        re.MULTILINE)
    m2 = pat_e2.search(body)
    if not m2:
        return [("Глава I", body, "02_character_creation.txt")]
    pat_e3 = re.compile(r"^#+\s*Этап\s*3\s*[.:]", re.MULTILINE)
    m3 = pat_e3.search(body, m2.end())
    parts = []
    parts.append(("Глава I: Этапы 1, 5, 6, 7",
                  body[:m2.start()].strip(),
                  "02_character_creation.txt"))
    if m3:
        parts.append(("Путь Происхождения",
                      body[m2.start():m3.start()].strip(),
                      "02a_origin_path.txt"))
        parts.append(("Глава I: Этапы 3-4, 6-7",
                      body[m3.start():].strip(),
                      "02_character_creation.txt"))
    else:
        parts.append(("Путь Происхождения",
                      body[m2.start():].strip(),
                      "02a_origin_path.txt"))
    return parts


def split_armory(body: str):
    pat = re.compile(r"^#+\s*Броня\s*$", re.MULTILINE)
    m = pat.search(body)
    if not m:
        return [("Арсенал", body, "06_weapons.txt")]
    return [
        ("Арсенал: Оружие, Боеприпасы, Модификации",
         body[:m.start()].strip(), "06_weapons.txt"),
        ("Арсенал: Броня, Снаряжение, Кибернетика",
         body[m.start():].strip(), "07_armor.txt"),
    ]


def split_gameplay(body: str):
    sections = [
        ("Проверки",          "01_core_mechanics.txt"),
        ("Роль Судьбы",       "01_core_mechanics.txt"),
        ("Бой",               "03_combat.txt"),
        ("Ранения",           "03_combat.txt"),
        ("Исследование",      "03_combat.txt"),
        ("Движение",          "03_combat.txt"),
        ("Фактор Прибыли",    "01_core_mechanics.txt"),
        ("Приобретение",      "01_core_mechanics.txt"),
        ("Влияние",           "01_core_mechanics.txt"),
        ("Предприятия",       "01_core_mechanics.txt"),
        ("Неудачи",           "01_core_mechanics.txt"),
    ]
    positions = []
    for name, target in sections:
        pat = re.compile(r"^#+\s*" + re.escape(name) + r"\s*$", re.MULTILINE)
        for m in pat.finditer(body):
            positions.append((m.start(), name, target))
    positions.sort()
    if not positions:
        return [("Игровой Процесс", body, "01_core_mechanics.txt")]
    result = []
    for i, (pos, name, target) in enumerate(positions):
        end = positions[i + 1][0] if i + 1 < len(positions) else len(body)
        result.append((name, body[pos:end].strip(), target))
    return result


def _append(target: Path, content: str, title: str, key: str,
            report: dict, extra_header: str = ""):
    marker = "MARKER: " + TAG + "::" + key
    if target.exists():
        existing = target.read_text(encoding="utf-8", errors="replace")
        if marker in existing:
            report["skipped"].append(str(target.relative_to(ROOT)) + " :: " + key)
            return
        bak = target.with_suffix(target.suffix + ".bak_pre_" + TAG)
        if not bak.exists():
            try:
                shutil.copy2(target, bak)
            except Exception:
                pass
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        existing = ""
    header = MARKER_TEMPLATE.format(title=title, tag=TAG, key=key)
    payload = existing + header + extra_header + content + "\n"
    target.write_text(payload, encoding="utf-8")
    report["modified"].append(str(target.relative_to(ROOT)) + " :: " + key)


def main() -> None:
    report = {"modified": [], "skipped": [], "errors": []}
    path = find_book()
    print("[info] Книга:", path)
    doc = Document(str(path))
    print("[info] Параграфов:", len(doc.paragraphs),
          "Таблиц:", len(doc.tables))
    chapters = collect_chapters(doc)
    print("[info] Распознано разделов:", len(chapters))
    for roman, title, blocks in chapters:
        print("   ", roman, "|", title[:60], "|", len(blocks), "блоков")

    for roman, title, blocks in chapters:
        body = blocks_to_text(blocks)
        if not body.strip():
            continue
        if roman == "intro":
            target = DATA / "general" / "01_core_mechanics.txt"
            _append(target, body, "Вступление", "intro::core", report)
            continue
        cls = CHAPTER_MAP.get(roman)
        if not cls:
            report["errors"].append("Нет маппинга для Главы " + roman)
            continue
        folder, filename = cls
        if filename == "__CHARACTER__":
            for pt, pb, fname in split_character(body):
                target = DATA / "general" / fname
                _append(target, pb, pt, "I::" + pt[:40], report)
            continue
        if filename == "__ARMORY__":
            for pt, pb, fname in split_armory(body):
                target = DATA / "general" / fname
                _append(target, pb, pt, "V::" + pt[:40], report)
            continue
        if filename == "__GAMEPLAY__":
            for pt, pb, fname in split_gameplay(body):
                target = DATA / "general" / fname
                _append(target, pb, pt, "IX::" + pt[:40], report)
            continue
        target = DATA / folder / filename
        extra = MAW_HEADER if roman == "XV" else ""
        _append(target, body, title, roman + "::" + title[:40],
                report, extra_header=extra)

    print("")
    print("=== SPLIT_RULEBOOK " + TAG + " ===")
    for k in ("modified", "skipped"):
        for p in report[k]:
            print("  [" + k.upper() + "] " + p)
    for e in report["errors"]:
        print("  [ERROR] " + e)
    print("")
    print("DONE - ok" if not report["errors"] else "DONE (with errors)")


if __name__ == "__main__":
    main()
