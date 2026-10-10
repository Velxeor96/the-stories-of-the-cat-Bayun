# scripts/patch.py — PATCH_85: clean Library UI (single field, no source paths)
from __future__ import annotations
import ast, re, shutil, sys
from pathlib import Path

TAG = "PATCH_85"
ROOT = Path(__file__).resolve().parent.parent
if not (ROOT / "app.py").exists():
    print("[ERROR] app.py не найден.")
    sys.exit(1)

r = {"modified": [], "errors": [], "warns": []}


def _bk(p):
    b = p.with_suffix(p.suffix + ".bak_pre_" + TAG)
    if not b.exists() and p.exists():
        try:
            shutil.copy2(p, b)
        except Exception:
            pass


lib_path = ROOT / "ui" / "screens" / "library.py"
if not lib_path.exists():
    print("[ERROR] ui/screens/library.py не найден.")
    sys.exit(1)

_bk(lib_path)
src = lib_path.read_text(encoding="utf-8")

# Определяем, куда ведёт "← Назад"
back_targets = re.findall(
    r"st\.session_state\.screen\s*=\s*[\"']([\w_]+)[\"']", src
)
back_target = back_targets[0] if back_targets else "main_menu"
back_target = re.sub(r"[^a-zA-Z0-9_]", "", back_target) or "main_menu"
r["warns"].append("Назад -> " + back_target)

# Новый модуль-содержимое (заменит render() и добавит хелперы)
NEW_RENDER = (
    "def render():\n"
    '    """Чистый экран Библиотеки: запрос + ответ одним блоком."""\n'
    "    import streamlit as st\n"
    "\n"
    '    st.markdown("## 📚 Библиотека")\n'
    "\n"
    "    c1, c2 = st.columns([5, 1])\n"
    "    with c2:\n"
    '        if st.button("← Назад", key="library_back", use_container_width=True):\n'
    '            st.session_state.screen = "' + back_target + '"\n'
    "            try:\n"
    "                st.rerun()\n"
    "            except AttributeError:\n"
    "                st.experimental_rerun()\n"
    "            return\n"
    "    with c1:\n"
    "        query = st.text_input(\n"
    '            "Запрос",\n'
    '            key="library_query",\n'
    '            placeholder="Например: Что такое Инквизиция?",\n'
    '            label_visibility="collapsed",\n'
    "        )\n"
    "\n"
    "    if not query:\n"
    '        st.caption("Введите запрос — я поищу ответ в архивах.")\n'
    "        return\n"
    "\n"
    '    with st.spinner("Ищу в архивах..."):\n'
    "        results = _library_search(query, k=6)\n"
    "\n"
    "    if not results:\n"
    '        st.warning("Ничего не найдено.")\n'
    "        return\n"
    "\n"
    "    parts = []\n"
    "    for item in results:\n"
    "        text = _library_chunk_text(item)\n"
    "        if text and text.strip():\n"
    "            parts.append(_library_clean(text).strip())\n"
    "\n"
    '    combined = "\\n\\n".join(p for p in parts if p)\n'
    "    if not combined.strip():\n"
    '        st.info("Ничего полезного в найденных фрагментах.")\n'
    "        return\n"
    "\n"
    '    st.markdown("---")\n'
    "    st.markdown(combined)\n"
    "\n"
    "\n"
    "def _library_search(query, k=6):\n"
    '    """Универсальный поиск по RAG-хранилищу."""\n'
    "    candidates = [\n"
    '        ("services.rag", ("search", "query", "retrieve", "get_context", "find")),\n'
    '        ("services.knowledge", ("search", "query", "retrieve")),\n'
    '        ("services.library", ("search", "query", "retrieve")),\n'
    '        ("services.orchestrator", ("rag_query", "rag_search", "search")),\n'
    '        ("orchestrator", ("rag_query", "rag_search", "search")),\n'
    "    ]\n"
    "    for mod_name, fn_names in candidates:\n"
    "        try:\n"
    '            mod = __import__(mod_name, fromlist=["*"])\n'
    "        except Exception:\n"
    "            continue\n"
    "        for fn_name in fn_names:\n"
    "            fn = getattr(mod, fn_name, None)\n"
    "            if not callable(fn):\n"
    "                continue\n"
    "            for kw in ({\"k\": k}, {\"top_k\": k}, {}):\n"
    "                try:\n"
    "                    out = fn(query, **kw)\n"
    "                except TypeError:\n"
    "                    continue\n"
    "                except Exception:\n"
    "                    continue\n"
    "                if out:\n"
    "                    return out\n"
    "    return []\n"
    "\n"
    "\n"
    "def _library_chunk_text(item):\n"
    '    """Достаёт текст из чанка (str / dict / tuple / object)."""\n'
    "    if item is None:\n"
    '        return ""\n'
    "    if isinstance(item, str):\n"
    "        return item\n"
    "    if isinstance(item, tuple) and len(item) >= 1:\n"
    "        return _library_chunk_text(item[0])\n"
    "    if isinstance(item, dict):\n"
    '        for k in ("page_content", "text", "content", "chunk", "document"):\n'
    "            if item.get(k):\n"
    "                return str(item[k])\n"
    '        return ""\n'
    '    for attr in ("page_content", "text", "content"):\n'
    "        v = getattr(item, attr, None)\n"
    "        if v:\n"
    "            return str(v)\n"
    "    return str(item)\n"
    "\n"
    "\n"
    "def _library_clean(text):\n"
    '    """Убирает «== Заголовок ==» из источника, оставляет текст."""\n'
    "    out = []\n"
    '    for line in str(text).split("\\n"):\n'
    "        s = line.strip()\n"
    "        if len(s) >= 4 and set(s) <= set(\"= \"):\n"
    "            continue\n"
    '        if s.startswith("==") and s.endswith("=="):\n'
    '            title = s.strip("= ").strip()\n'
    "            if title:\n"
    '                out.append("**" + title + "**")\n'
    "            continue\n"
    "        out.append(line)\n"
    '    return "\\n".join(out).strip()\n'
)

# Найдём границы render() через AST
try:
    tree = ast.parse(src)
except SyntaxError as e:
    print("[ERROR] library.py не парсится: " + str(e))
    sys.exit(1)

render_node = None
for node in tree.body:
    if isinstance(node, ast.FunctionDef) and node.name == "render":
        render_node = node
        break

lines = src.split("\n")

if render_node is None:
    r["warns"].append("render() не найден — добавляю в конец файла")
    new_src = src.rstrip() + "\n\n\n" + NEW_RENDER
else:
    start = render_node.lineno - 1
    end = render_node.end_lineno
    new_lines = lines[:start] + NEW_RENDER.split("\n") + lines[end:]
    new_src = "\n".join(new_lines)

try:
    ast.parse(new_src)
except SyntaxError as e:
    r["errors"].append("new library.py syntax: " + str(e))
    print("[ERROR] syntax: " + str(e))
    print("Откат из бэкапа .bak_pre_" + TAG)
    sys.exit(1)

lib_path.write_text(new_src, encoding="utf-8")
r["modified"].append("ui/screens/library.py — чистый UI (без путей источников)")


print("=== PATCH " + TAG + " ===")
for m in r["modified"]:
    print("  [MODIFIED] " + m)
for w in r["warns"]:
    print("  [WARN] " + w)
for e in r["errors"]:
    print("  [ERROR] " + e)
print("DONE" if not r["errors"] else "DONE (with errors)")