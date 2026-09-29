#!/usr/bin/env python3
# scripts/analyze.py
# Статический анализ проекта Wh40K.
# Пишет:
#   reports/code_analysis_<stamp>.md  (история)
#   reports/code_analysis_latest.md   (последний)
#   PROJECT_SNAPSHOT.md               (для вставки в чат)

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime


ROOT = Path(__file__).resolve().parent.parent
REPORTS = ROOT / "reports"
NL = chr(10)

SKIP_DIRS = {
    ".git", "__pycache__", ".venv", "venv", "node_modules",
    "reports", ".pytest_cache", ".mypy_cache", ".idea", ".vscode",
    "dist", "build",
}

ENTRYPOINTS = {"app.py"}

WIDGET_NAMES = {
    "button", "download_button", "checkbox", "radio", "selectbox",
    "multiselect", "slider", "select_slider", "text_input",
    "text_area", "number_input", "date_input", "time_input",
    "file_uploader", "color_picker", "form", "form_submit_button",
    "toggle", "chat_input", "camera_input",
}


def iter_py_files():
    out = []
    for p in ROOT.rglob("*.py"):
        try:
            rel = p.relative_to(ROOT)
        except ValueError:
            continue
        if any(part in SKIP_DIRS for part in rel.parts):
            continue
        out.append(p)
    return sorted(out)


def rel_of(p):
    return "/".join(p.relative_to(ROOT).parts)


def module_of(rel):
    if rel.endswith("/__init__.py"):
        return rel[: -len("/__init__.py")].replace("/", ".")
    if rel.endswith(".py"):
        return rel[:-3].replace("/", ".")
    return rel


def attr_chain(node):
    names = []
    cur = node
    while isinstance(cur, ast.Attribute):
        names.append(cur.attr)
        cur = cur.value
    if isinstance(cur, ast.Name):
        names.append(cur.id)
        names.reverse()
        return names
    return None


def is_st_chain(node, tail):
    chain = attr_chain(node)
    if not chain or chain[0] != "st":
        return False
    return chain[1:] == tail


def is_st_rooted(node):
    cur = node
    while True:
        if isinstance(cur, ast.Name):
            return cur.id == "st"
        if isinstance(cur, ast.Attribute):
            cur = cur.value
            continue
        if isinstance(cur, ast.Subscript):
            cur = cur.value
            continue
        if isinstance(cur, ast.Call):
            cur = cur.func
            continue
        return False


def last_attr(node):
    f = node
    while True:
        if isinstance(f, ast.Subscript):
            f = f.value
            continue
        if isinstance(f, ast.Call):
            f = f.func
            continue
        break
    if isinstance(f, ast.Attribute):
        return f.attr
    return None


def ss_key_of(node):
    if isinstance(node, ast.Attribute):
        chain = attr_chain(node)
        if chain and len(chain) == 3 and chain[0] == "st" and chain[1] == "session_state":
            return chain[2]
    if isinstance(node, ast.Subscript):
        if is_st_chain(node.value, ["session_state"]):
            sl = node.slice
            if isinstance(sl, ast.Constant) and isinstance(sl.value, str):
                return sl.value
    return None


def is_ss_call(node):
    if not isinstance(node, ast.Call):
        return None
    f = node.func
    if not isinstance(f, ast.Attribute):
        return None
    chain = attr_chain(f.value)
    if chain == ["st", "session_state"]:
        return f.attr
    return None


def const_str(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def top_level_dict_keys(tree):
    out = {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    if isinstance(node.value, ast.Dict):
                        keys = []
                        for k in node.value.keys:
                            if isinstance(k, ast.Constant):
                                keys.append(k.value)
                            else:
                                keys.append("?")
                        out[t.id] = ("dict", keys)
                    elif isinstance(node.value, (ast.List, ast.Tuple)):
                        out[t.id] = ("list", len(node.value.elts))
    return out


def analyze_file(p):
    rel = rel_of(p)
    src = p.read_text(encoding="utf-8", errors="replace")
    info = {
        "rel": rel,
        "loc": src.count(NL) + 1,
        "tree": None,
        "doc": None,
        "syntax_error": None,
        "imports": [],
        "widgets": [],
        "ss_writes": [],
        "ss_reads": [],
        "css_violations": [],
        "bare_excepts": [],
        "icon_empty": [],
        "top_funcs": [],
        "top_classes": [],
        "todos": [],
        "constants": {},
    }
    try:
        tree = ast.parse(src)
    except SyntaxError as e:
        info["syntax_error"] = "line " + str(e.lineno) + ": " + str(e.msg)
        return info
    info["tree"] = tree
    info["doc"] = ast.get_docstring(tree)
    info["constants"] = top_level_dict_keys(tree)

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            end = getattr(node, "end_lineno", node.lineno)
            info["top_funcs"].append((node.name, node.lineno, end - node.lineno + 1))
        elif isinstance(node, ast.ClassDef):
            end = getattr(node, "end_lineno", node.lineno)
            info["top_classes"].append((node.name, node.lineno, end - node.lineno + 1))

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                info["imports"].append((a.name, node.lineno))
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            for a in node.names:
                full = (base + "." + a.name) if base else a.name
                info["imports"].append((full, node.lineno))

    write_target_ids = set()
    for node in ast.walk(tree):
        targets = []
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, (ast.AnnAssign, ast.AugAssign)):
            targets = [node.target]
        for t in targets:
            key = ss_key_of(t)
            if key:
                info["ss_writes"].append((key, node.lineno))
                write_target_ids.add(id(t))

    for node in ast.walk(tree):
        key = ss_key_of(node)
        if key and id(node) not in write_target_ids:
            info["ss_reads"].append((key, node.lineno))

    for node in ast.walk(tree):
        method = is_ss_call(node)
        if not method:
            continue
        key = const_str(node.args[0]) if node.args else None
        if not key:
            continue
        if method in ("get", "setdefault", "__contains__"):
            info["ss_reads"].append((key, node.lineno))
        elif method == "pop":
            info["ss_writes"].append((key, node.lineno))
            info["ss_reads"].append((key, node.lineno))

    for node in ast.walk(tree):
        if isinstance(node, ast.Compare):
            for i, op in enumerate(node.ops):
                if not isinstance(op, ast.In):
                    continue
                left = node.left if i == 0 else node.comparators[i - 1]
                right = node.comparators[i]
                if is_st_chain(right, ["session_state"]):
                    sv = const_str(left)
                    if sv:
                        info["ss_reads"].append((sv, node.lineno))

    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and is_st_rooted(node.func):
            if is_ss_call(node) is not None:
                continue
            name = last_attr(node)
            if not name:
                continue
            label = ""
            if node.args:
                lab = const_str(node.args[0])
                if lab:
                    label = lab
            info["widgets"].append((name, label, node.lineno))
            for kw in node.keywords:
                if kw.arg == "icon":
                    if isinstance(kw.value, ast.Constant) and kw.value.value == "":
                        info["icon_empty"].append(node.lineno)

    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler) and node.type is None:
            info["bare_excepts"].append(node.lineno)
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            s = node.value
            if "{" in s and "}" in s:
                if "* {" in s or "*{" in s or ",* " in s or ",*{" in s:
                    info["css_violations"].append((node.lineno, "universal selector *"))

    for i, line in enumerate(src.split(NL), 1):
        for token in ("TODO", "FIXME", "XXX", "HACK"):
            if token in line:
                info["todos"].append((i, token, line.strip()))
                break

    return info


def find_screens_registry(data):
    for rel, info in data.items():
        tree = info["tree"]
        if tree is None:
            continue
        for node in tree.body:
            if isinstance(node, ast.Assign):
                for t in node.targets:
                    if isinstance(t, ast.Name) and t.id == "SCREENS":
                        if isinstance(node.value, ast.Dict):
                            keys = []
                            for k in node.value.keys:
                                if isinstance(k, ast.Constant):
                                    keys.append(k.value)
                            return rel, keys
    return None, []


def find_render_functions(data):
    out = {}
    for rel, info in data.items():
        if not rel.startswith("ui/screens/") and rel != "app.py":
            continue
        for name, lineno, length in info["top_funcs"]:
            if name == "render":
                out[rel] = lineno
    return out


def skeleton(obj):
    if isinstance(obj, dict):
        return {k: skeleton(v) for k, v in obj.items()}
    if isinstance(obj, list):
        if not obj:
            return []
        return [skeleton(obj[0])]
    if isinstance(obj, str):
        return ""
    if isinstance(obj, bool):
        return False
    if isinstance(obj, int):
        return 0
    if isinstance(obj, float):
        return 0.0
    return None


def read_version():
    v = ROOT / "VERSION"
    if v.exists():
        try:
            return v.read_text(encoding="utf-8").strip()
        except Exception:
            return "?"
    return "?"


def read_requirements():
    r = ROOT / "requirements.txt"
    if not r.exists():
        return []
    out = []
    try:
        for line in r.read_text(encoding="utf-8").split(NL):
            line = line.strip()
            if line and not line.startswith("#"):
                out.append(line)
    except Exception:
        pass
    return out


def find_sample_character():
    users_dir = ROOT / "data" / "users"
    if not users_dir.exists():
        return None
    for p in sorted(users_dir.glob("*/characters/*.json")):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(data, dict):
            return p, data
    return None


def render_tree(paths, max_per_dir=40):
    from collections import OrderedDict
    tree = OrderedDict()
    for rel in paths:
        parts = rel.split("/")
        cur = tree
        for i, part in enumerate(parts):
            if i == len(parts) - 1:
                cur.setdefault("__files__", []).append(part)
            else:
                cur = cur.setdefault(part, OrderedDict())
    lines = []
    def rec(node, prefix):
        if "__files__" in node:
            for f in sorted(node["__files__"])[:max_per_dir]:
                lines.append(prefix + f)
        for k in sorted(k for k in node.keys() if k != "__files__"):
            lines.append(prefix + k + "/")
            rec(node[k], prefix + "  ")
    rec(tree, "")
    return lines


def build_detailed(data, graph, reverse, cycles, dead,
                   reg_rel, reg_keys, render_funcs,
                   writes_by_key, reads_by_key,
                   orphan_writes, orphan_reads, multi_writers,
                   term_hits, css_hits, icon_hits, bare, todos,
                   long_files, long_funcs):
    lines = []
    def h1(s): lines.append("# " + s); lines.append("")
    def h2(s): lines.append("## " + s); lines.append("")
    def h3(s): lines.append("### " + s); lines.append("")
    def p(s): lines.append(s)
    def bullet(s): lines.append("- " + s)
    def blank(): lines.append("")

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    h1("Анализ кода Wh40K")
    p("Сгенерировано: " + now)
    p("Корень: " + str(ROOT))
    p("Файлов .py: " + str(len(data)))
    p("Всего строк: " + str(sum(v["loc"] for v in data.values())))
    blank()

    h2("1. Обзор")
    p("**Топ-15 файлов по LOC:**")
    blank()
    for rel, info in sorted(data.items(), key=lambda kv: kv[1]["loc"], reverse=True)[:15]:
        bullet(rel + " — " + str(info["loc"]) + " строк")
    blank()

    err_files = [(rel, i["syntax_error"]) for rel, i in data.items() if i["syntax_error"]]
    if err_files:
        h2("!! Файлы с ошибками синтаксиса")
        for rel, err in err_files:
            bullet(rel + " — " + str(err))
        blank()

    h2("2. Граф импортов")
    p("**Самые импортируемые модули:**")
    blank()
    for rel, importers in sorted(reverse.items(), key=lambda kv: len(kv[1]), reverse=True)[:10]:
        bullet(rel + " — импортируется " + str(len(importers)) + " раз")
    blank()
    p("**Модули, импортирующие больше всех:**")
    blank()
    for rel, deps in sorted(graph.items(), key=lambda kv: len(kv[1]), reverse=True)[:10]:
        bullet(rel + " — импортирует " + str(len(deps)))
    blank()
    if cycles:
        h3("Циклы импортов")
        for a, b in sorted(cycles):
            bullet(a + " <-> " + b)
        blank()
    else:
        p("Циклов импортов не обнаружено.")
        blank()
    if dead:
        h3("Модули-сироты (никто не импортирует)")
        for rel in dead:
            bullet(rel)
        blank()

    h2("3. Экраны")
    if reg_rel:
        p("Реестр SCREENS: `" + reg_rel + "` (" + str(len(reg_keys)) + " ключей)")
        blank()
        for k in reg_keys:
            expected = "ui/screens/" + str(k) + ".py"
            if expected in data:
                ok = "render() ok" if expected in render_funcs else "БЕЗ render()!"
                bullet(str(k) + " -> " + expected + " [" + ok + "]")
            else:
                bullet(str(k) + " -> " + expected + " [НЕ НАЙДЕН]")
        blank()
        extra = [rel for rel in render_funcs if Path(rel).stem not in reg_keys]
        if extra:
            h3("render() вне реестра")
            for rel in extra:
                bullet(rel)
            blank()

    h2("4. Session state")
    p("Ключей с записью: " + str(len(writes_by_key)) + ", с чтением: " + str(len(reads_by_key)))
    blank()
    if multi_writers:
        h3("Пишутся из нескольких мест")
        for k in multi_writers:
            p("**" + str(k) + "**")
            for rel, ln in writes_by_key[k]:
                bullet(rel + ":" + str(ln))
        blank()
    if orphan_writes:
        h3("Только запись")
        for k in orphan_writes:
            first = writes_by_key[k][0]
            bullet(str(k) + " (" + first[0] + ":" + str(first[1]) + ")")
        blank()
    if orphan_reads:
        h3("Только чтение")
        for k in orphan_reads:
            first = reads_by_key[k][0]
            bullet(str(k) + " (" + first[0] + ":" + str(first[1]) + ")")
        blank()

    h2("5. Streamlit-виджеты")
    widget_counter = Counter()
    for info in data.values():
        for name, label, ln in info["widgets"]:
            widget_counter[name] += 1
    p("Всего вызовов: " + str(sum(widget_counter.values())))
    blank()
    for name, cnt in widget_counter.most_common(20):
        bullet(str(name) + " — " + str(cnt))
    blank()

    h2("6. Правила HANDOFF")
    if term_hits:
        p("**Терминология:**")
        for rel, ln, term in term_hits:
            bullet(rel + ":" + str(ln) + " — " + term)
        blank()
    else:
        p("Нарушений терминологии нет.")
        blank()
    if css_hits:
        p("**CSS:**")
        for rel, ln, reason in css_hits:
            bullet(rel + ":" + str(ln) + " — " + reason)
        blank()
    else:
        p("CSS-нарушений нет.")
        blank()
    if icon_hits:
        p("**icon=\\\"\\\" в API:**")
        for rel, ln in icon_hits:
            bullet(rel + ":" + str(ln))
        blank()
    else:
        p("icon=\\\"\\\" нет.")
        blank()

    h2("7. Код-смеллы")
    if bare:
        h3("Bare except")
        for rel, ln in bare:
            bullet(rel + ":" + str(ln))
        blank()
    if todos:
        h3("TODO / FIXME")
        for rel, ln, tok, snip in todos:
            bullet(rel + ":" + str(ln) + " [" + tok + "]")
        blank()
    if long_files:
        h3("Файлы > 500 строк")
        for rel, loc in sorted(long_files, key=lambda x: -x[1]):
            bullet(rel + " — " + str(loc))
        blank()
    if long_funcs:
        h3("Функции > 80 строк")
        for rel, name, lineno, length in sorted(long_funcs, key=lambda x: -x[3]):
            bullet(rel + ":" + str(lineno) + " " + name + " — " + str(length) + " строк")
        blank()

    return NL.join(lines)


def build_snapshot(data, graph, reverse, cycles, dead,
                   reg_rel, reg_keys, render_funcs,
                   writes_by_key, reads_by_key,
                   term_hits, css_hits, icon_hits, bare, todos):
    lines = []
    def h1(s): lines.append("# " + s); lines.append("")
    def h2(s): lines.append("## " + s); lines.append("")
    def h3(s): lines.append("### " + s); lines.append("")
    def p(s): lines.append(s)
    def bullet(s): lines.append("- " + s)
    def code(s): lines.append("    " + s)
    def blank(): lines.append("")

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    h1("PROJECT SNAPSHOT — Wh40K RPG")
    p("Сгенерировано: " + now)
    p("")
    p("Это компактный снимок проекта для передачи в новый чат. " +
      "Подробный отчёт — в `reports/code_analysis_latest.md`.")
    blank()

    h2("Мета")
    bullet("VERSION: " + read_version())
    bullet("Python-файлов: " + str(len(data)))
    bullet("Строк кода: " + str(sum(v["loc"] for v in data.values())))
    reqs = read_requirements()
    if reqs:
        bullet("Зависимости: " + ", ".join(reqs))
    blank()

    h2("Структура (по .py-файлам)")
    p("```")
    for line in render_tree(sorted(data.keys())):
        code(line)
    p("```")
    blank()

    h2("Экраны (реестр SCREENS)")
    if reg_rel:
        bullet("Реестр: " + reg_rel)
        for k in reg_keys:
            expected = "ui/screens/" + str(k) + ".py"
            if expected in data:
                ok = "ok" if expected in render_funcs else "БЕЗ render()"
                bullet(str(k) + " -> " + expected + " [" + ok + "]")
            else:
                bullet(str(k) + " -> " + expected + " [НЕ НАЙДЕН]")
    else:
        p("Реестр SCREENS не найден.")
    blank()

    h2("Модули")
    for prefix in ("services/", "ui/screens/", "persistence/", "core/"):
        mods = sorted(rel for rel in data if rel.startswith(prefix))
        if not mods:
            continue
        h3(prefix)
        for rel in mods:
            doc = data[rel].get("doc")
            first = ""
            if doc:
                for line in doc.strip().split(NL):
                    if line.strip():
                        first = line.strip()
                        break
            bullet(rel + (" — " + first if first else ""))
        blank()

    h2("Ключевые константы верхнего уровня")
    found_const = False
    for rel in sorted(data.keys()):
        if not (rel.startswith("services/") or rel.startswith("core/")):
            continue
        consts = data[rel].get("constants") or {}
        if not consts:
            continue
        p("**" + rel + "**")
        for name, (kind, val) in consts.items():
            if kind == "dict":
                keys = val
                if len(keys) <= 25:
                    bullet(name + " (dict): " + ", ".join(str(x) for x in keys))
                else:
                    bullet(name + " (dict, " + str(len(keys)) + " ключей)")
            elif kind == "list":
                bullet(name + " (list, " + str(val) + " эл.)")
        found_const = True
    if not found_const:
        p("Констант не найдено.")
    blank()

    h2("Формат листа персонажа")
    sample = find_sample_character()
    if sample:
        path, obj = sample
        p("Пример: `" + rel_of(path) + "`")
        p("```json")
        sk = json.dumps(skeleton(obj), ensure_ascii=False, indent=2)
        for line in sk.split(NL):
            code(line)
        p("```")
    else:
        p("Ни одного файла персонажа не найдено.")
    blank()

    h2("Session state (сводка)")
    bullet("Ключей с записью: " + str(len(writes_by_key)))
    bullet("Ключей с чтением: " + str(len(reads_by_key)))
    blank()
    all_keys = set(writes_by_key) | set(reads_by_key)
    for k in sorted(all_keys):
        w = len(writes_by_key.get(k, []))
        r = len(reads_by_key.get(k, []))
        bullet(str(k) + " — write=" + str(w) + ", read=" + str(r))
    blank()

    h2("Импорт-граф")
    if cycles:
        p("**Циклы:**")
        for a, b in sorted(cycles):
            bullet(a + " <-> " + b)
        blank()
    else:
        p("Циклов нет.")
        blank()
    if dead:
        p("**Модули-сироты:**")
        for rel in dead:
            bullet(rel)
        blank()

    h2("Проблемы / нарушения")
    problems = False
    if term_hits:
        problems = True
        p("**Терминология:**")
        for rel, ln, term in term_hits:
            bullet(rel + ":" + str(ln) + " — " + term)
        blank()
    if css_hits:
        problems = True
        p("**CSS:**")
        for rel, ln, reason in css_hits:
            bullet(rel + ":" + str(ln) + " — " + reason)
        blank()
    if icon_hits:
        problems = True
        p("**icon в API:**")
        for rel, ln in icon_hits:
            bullet(rel + ":" + str(ln))
        blank()
    if bare:
        problems = True
        p("**Bare except:** " + str(len(bare)) + " шт.")
        blank()
    if todos:
        problems = True
        p("**TODO/FIXME:** " + str(len(todos)) + " шт.")
        blank()
    if not problems:
        p("Явных проблем не найдено.")
    blank()

    p("---")
    p("Конец снимка.")

    return NL.join(lines)


def main():
    files = iter_py_files()
    data = {rel_of(p): analyze_file(p) for p in files}
    modules = {module_of(rel): rel for rel in data}

    graph = defaultdict(set)
    reverse = defaultdict(set)
    for rel, info in data.items():
        for name, _ in info["imports"]:
            target_rel = None
            if name in modules:
                target_rel = modules[name]
            else:
                parts = name.split(".")
                for i in range(len(parts), 0, -1):
                    cand = ".".join(parts[:i])
                    if cand in modules:
                        target_rel = modules[cand]
                        break
            if target_rel and target_rel != rel:
                graph[rel].add(target_rel)
                reverse[target_rel].add(rel)

    cycles = set()
    for a, deps in graph.items():
        for b in deps:
            if a in graph.get(b, set()):
                cycles.add(tuple(sorted([a, b])))

    dead = []
    for rel in data:
        if rel in ENTRYPOINTS:
            continue
        if rel.startswith("scripts/"):
            continue
        if rel.endswith("__init__.py"):
            continue
        if rel not in reverse:
            dead.append(rel)

    reg_rel, reg_keys = find_screens_registry(data)
    render_funcs = find_render_functions(data)

    writes_by_key = defaultdict(list)
    reads_by_key = defaultdict(list)
    for rel, info in data.items():
        for key, ln in info["ss_writes"]:
            writes_by_key[key].append((rel, ln))
        for key, ln in info["ss_reads"]:
            reads_by_key[key].append((rel, ln))

    orphan_writes = sorted(k for k in writes_by_key if k not in reads_by_key)
    orphan_reads = sorted(k for k in reads_by_key if k not in writes_by_key)
    multi_writers = sorted(k for k, v in writes_by_key.items() if len(v) > 1)

    term_hits = []
    for rel in data.keys():
        pth = ROOT / rel
        try:
            src = pth.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        for i, line in enumerate(src.split(NL), 1):
            if "Варрант" in line:
                term_hits.append((rel, i, "Варрант"))
            if "Товарищество" in line:
                term_hits.append((rel, i, "Товарищество"))

    css_hits = [(rel, ln, reason) for rel, info in data.items()
                for ln, reason in info["css_violations"]]
    icon_hits = [(rel, ln) for rel, info in data.items() for ln in info["icon_empty"]]
    bare = [(rel, ln) for rel, info in data.items() for ln in info["bare_excepts"]]
    todos = [(rel, ln, tok, snip) for rel, info in data.items()
             for ln, tok, snip in info["todos"]]

    long_files = [(rel, info["loc"]) for rel, info in data.items() if info["loc"] > 500]
    long_funcs = []
    for rel, info in data.items():
        for name, lineno, length in info["top_funcs"]:
            if length > 80:
                long_funcs.append((rel, name, lineno, length))

    detailed = build_detailed(
        data, graph, reverse, cycles, dead,
        reg_rel, reg_keys, render_funcs,
        writes_by_key, reads_by_key,
        orphan_writes, orphan_reads, multi_writers,
        term_hits, css_hits, icon_hits, bare, todos,
        long_files, long_funcs,
    )

    snapshot = build_snapshot(
        data, graph, reverse, cycles, dead,
        reg_rel, reg_keys, render_funcs,
        writes_by_key, reads_by_key,
        term_hits, css_hits, icon_hits, bare, todos,
    )

    REPORTS.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = REPORTS / ("code_analysis_" + stamp + ".md")
    latest = REPORTS / "code_analysis_latest.md"
    out_path.write_text(detailed, encoding="utf-8")
    latest.write_text(detailed, encoding="utf-8")

    snap_path = ROOT / "PROJECT_SNAPSHOT.md"
    snap_path.write_text(snapshot, encoding="utf-8")

    print("Analyzed " + str(len(data)) + " files, " +
          str(sum(v["loc"] for v in data.values())) + " LOC")
    print("Detailed: " + str(out_path.relative_to(ROOT)))
    print("Latest:   " + str(latest.relative_to(ROOT)))
    print("Snapshot: " + str(snap_path.relative_to(ROOT)))
    if any(v["syntax_error"] for v in data.values()):
        print("WARNING: syntax errors in some files")
    if cycles:
        print("WARNING: import cycles: " + str(len(cycles)))
    if term_hits or css_hits or icon_hits:
        print("WARNING: HANDOFF violations found")


if __name__ == "__main__":
    main()
