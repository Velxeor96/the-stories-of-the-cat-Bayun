# scripts/patch.py
# PATCH_15U — SVG-fallback Эльдар = "Глаз Иши" (глаз с слезой).
# VERSION -> 1.0.5. CHANGELOG -> [1.0.5].
# Запуск: python scripts\patch.py
from __future__ import annotations

import ast
import shutil
import sys
from pathlib import Path

TAG = "PATCH_15U"
ROOT = Path(__file__).resolve().parent.parent
FILES: dict[str, str] = {}


FILES["VERSION"] = "1.0.5\n"


FILES["ui/assets.py"] = r"""# PATCH_15U
# ui/assets.py — сиглы фракций.
# Fallback Эльдар = "Глаз Иши": стилизованный глаз с слезой.
from __future__ import annotations

import base64
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_SIGILS_DIR = _ROOT / "static" / "sigils"

_CACHE: dict[str, object] = {}
_ID: list = [0]
_PNG_SIG = b"\x89PNG\r\n\x1a\n"


def _nid(prefix: str) -> str:
    _ID[0] += 1
    return prefix + "_" + str(_ID[0])


def sigil_svg(theme: str = "dark", size: int = 96) -> str:
    raw = _load_raw(theme)
    if raw is not None:
        kind, content = raw  # type: ignore
        if kind == "svg":
            return _fit_svg_inline(str(content), size)
        if kind == "png":
            return _fit_png_colorized(str(content), size, theme)
    fn = _DISPATCH.get(theme, _dark)
    return fn(size)


def _load_raw(theme: str):
    if theme in _CACHE:
        return _CACHE[theme]
    svg_p = _SIGILS_DIR / (theme + ".svg")
    png_p = _SIGILS_DIR / (theme + ".png")
    result = None
    try:
        if svg_p.exists():
            result = ("svg", svg_p.read_text(encoding="utf-8"))
            print("[assets] " + theme + ".svg loaded ("
                  + str(len(result[1])) + " chars)")
        elif png_p.exists():
            data = png_p.read_bytes()
            if len(data) < 8 or data[:8] != _PNG_SIG:
                print("[assets] " + theme + ".png has non-PNG signature ("
                      + str(len(data)) + " bytes) -> fallback")
                result = None
            else:
                result = ("png", base64.b64encode(data).decode("ascii"))
                print("[assets] " + theme + ".png loaded ("
                      + str(len(data)) + " bytes)")
        else:
            print("[assets] " + theme + ": no PNG/SVG in static/sigils")
    except Exception as e:
        print("[assets] load " + theme + " fail: "
              + type(e).__name__ + ": " + str(e))
        result = None
    _CACHE[theme] = result
    return result


def _accent_rgb() -> tuple:
    hexc = "#b03030"
    try:
        from ui.theme import THEMES, _current
        t = THEMES.get(_current(), THEMES.get("dark", {}))
        hexc = str(t.get("vars", {}).get("--accent", hexc))
    except Exception as e:
        print("[assets] accent lookup fail: "
              + type(e).__name__ + ": " + str(e))
    hexc = hexc.strip().lstrip("#")
    if len(hexc) != 6:
        return (0.69, 0.19, 0.19)
    try:
        r = int(hexc[0:2], 16) / 255.0
        g = int(hexc[2:4], 16) / 255.0
        b = int(hexc[4:6], 16) / 255.0
        return (r, g, b)
    except Exception:
        return (0.69, 0.19, 0.19)


def _fmt(v: float) -> str:
    return format(v, ".4f")


def _fit_png_colorized(b64: str, size: int, theme: str) -> str:
    r, g, b = _accent_rgb()
    fid = _nid("sf_" + theme)
    fr = str(int(round(r * 255)))
    fg = str(int(round(g * 255)))
    fb = str(int(round(b * 255)))

    matrix = (
        "0 0 0 0 " + _fmt(r) + " "
        "0 0 0 0 " + _fmt(g) + " "
        "0 0 0 0 " + _fmt(b) + " "
        "-0.2126 -0.7152 -0.0722 0 1"
    )

    return (
        '<svg width="' + str(size) + '" height="' + str(size) + '" '
        'viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">'
        '<defs>'
        '<filter id="' + fid + '" x="-10%" y="-10%" '
        'width="120%" height="120%" color-interpolation-filters="sRGB">'
        '<feColorMatrix in="SourceGraphic" type="matrix" '
        'values="' + matrix + '" result="luma"/>'
        '<feComposite in="luma" in2="SourceGraphic" operator="in" '
        'result="masked"/>'
        '<feFlood flood-color="rgb(' + fr + ',' + fg + ',' + fb + ')" '
        'result="flood"/>'
        '<feComposite in="flood" in2="masked" operator="in"/>'
        '</filter>'
        '</defs>'
        '<image href="data:image/png;base64,' + b64 + '" '
        'x="0" y="0" width="100" height="100" '
        'preserveAspectRatio="xMidYMid meet" '
        'filter="url(#' + fid + ')"/>'
        '</svg>'
    )


def _strip_prefix(s: str) -> str:
    s = s.strip()
    if s.startswith("<?xml"):
        i = s.find("?>")
        if i >= 0:
            s = s[i + 2:].lstrip()
    while s.startswith("<!DOCTYPE"):
        i = s.find(">")
        if i < 0:
            break
        s = s[i + 1:].lstrip()
    while s.startswith("<!--"):
        i = s.find("-->")
        if i < 0:
            break
        s = s[i + 3:].lstrip()
    if not s.startswith("<svg"):
        i = s.find("<svg")
        if i >= 0:
            s = s[i:]
    return s


def _fit_svg_inline(svg_text: str, size: int) -> str:
    s = _strip_prefix(svg_text)
    style = ('style="width:' + str(size) + 'px;height:' + str(size) + 'px;"')
    if s.startswith("<svg "):
        s = "<svg " + style + " " + s[5:]
    elif s.startswith("<svg>"):
        s = "<svg " + style + ">" + s[5:]
    return s


def _wrap(size: int, body: str) -> str:
    return (
        '<svg width="' + str(size) + '" height="' + str(size) + '" '
        'viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">'
        + body + '</svg>'
    )


# --- Fallback SVG ---------------------------------------------------
def _imperial(size: int) -> str:
    body = (
        '<g fill="#d4a017" stroke="#7a5a10" stroke-width="0.5">'
        '<path d="M50 42 L92 20 L94 24 L52 45 Z"/>'
        '<path d="M50 46 L95 32 L96 36 L52 49 Z"/>'
        '<path d="M50 50 L96 44 L96 48 L52 53 Z"/>'
        '<path d="M50 54 L94 54 L93 58 L52 57 Z"/>'
        '<path d="M50 58 L90 64 L88 68 L52 61 Z"/>'
        '<path d="M50 42 L8 20 L6 24 L48 45 Z"/>'
        '<path d="M50 46 L5 32 L4 36 L48 49 Z"/>'
        '<path d="M50 50 L4 44 L4 48 L48 53 Z"/>'
        '<path d="M50 54 L6 54 L7 58 L48 57 Z"/>'
        '<path d="M50 58 L10 64 L12 68 L48 61 Z"/>'
        '<path d="M46 40 L50 78 L54 40 Z"/>'
        '<path d="M44 78 L50 92 L56 78 Z"/>'
        '<path d="M46 40 C 40 30 42 22 46 20 C 50 22 50 32 46 40 Z"/>'
        '<path d="M54 40 C 60 30 58 22 54 20 C 50 22 50 32 54 40 Z"/>'
        '</g>'
        '<path d="M42 22 L34 20 L42 26 Z" fill="#7a5a10"/>'
        '<path d="M58 22 L66 20 L58 26 Z" fill="#7a5a10"/>'
    )
    return _wrap(size, body)


def _mechanicum(size: int) -> str:
    teeth = []
    for i in range(16):
        ang = i * 22.5
        teeth.append(
            '<rect x="48" y="6" width="4" height="8" fill="#c83838" '
            'transform="rotate(' + str(ang) + ' 50 50)"/>'
        )
    body = (
        "".join(teeth)
        + '<circle cx="50" cy="50" r="38" fill="none" '
        'stroke="#a02020" stroke-width="2.5"/>'
        + '<circle cx="50" cy="50" r="34" fill="none" '
        'stroke="#c83838" stroke-width="1"/>'
        + '<line x1="50" y1="16" x2="50" y2="84" '
        'stroke="#e05050" stroke-width="1.6"/>'
        + '<path d="M50 30 C 60 30 66 38 66 50 '
        'C 66 58 62 64 60 66 L 60 72 L 40 72 L 40 66 '
        'C 38 64 34 58 34 50 C 34 38 40 30 50 30 Z" '
        'fill="#c83838" stroke="#7a1a1a" stroke-width="0.5"/>'
        + '<ellipse cx="46" cy="48" rx="3" ry="3.6" fill="#0a0505"/>'
        + '<ellipse cx="54" cy="48" rx="3" ry="3.6" fill="#0a0505"/>'
        + '<path d="M50 54 L48.5 58 L51.5 58 Z" fill="#0a0505"/>'
        + '<rect x="44" y="66" width="1.2" height="6" fill="#0a0505"/>'
        + '<rect x="47" y="66" width="1.2" height="6" fill="#0a0505"/>'
        + '<rect x="50" y="66" width="1.2" height="6" fill="#0a0505"/>'
        + '<rect x="53" y="66" width="1.2" height="6" fill="#0a0505"/>'
        + '<rect x="56" y="66" width="1.2" height="6" fill="#0a0505"/>'
    )
    return _wrap(size, body)


def _chaos(size: int) -> str:
    body = (
        '<path d="M50 5 L54 42 L88 20 L60 44 '
        'L95 50 L60 56 L88 80 L54 58 '
        'L50 95 L46 58 L12 80 L40 56 '
        'L5 50 L40 44 L12 20 L46 42 Z" '
        'fill="#a82020" stroke="#7a0a0a" stroke-width="0.6"/>'
        '<circle cx="50" cy="50" r="6" fill="#050202"/>'
        '<circle cx="50" cy="50" r="3" fill="#a82020"/>'
    )
    return _wrap(size, body)


def _imperial_guard(size: int) -> str:
    body = (
        '<g fill="#c8b878" stroke="#5a5a30" stroke-width="0.5">'
        '<path d="M45 46 L6 32 L4 36 L43 50 Z"/>'
        '<path d="M45 52 L4 46 L3 50 L43 55 Z"/>'
        '<path d="M45 58 L6 60 L8 64 L45 61 Z"/>'
        '<path d="M55 46 L94 32 L96 36 L57 50 Z"/>'
        '<path d="M55 52 L96 46 L97 50 L57 55 Z"/>'
        '<path d="M55 58 L94 60 L92 64 L55 61 Z"/>'
        '<path d="M50 34 C 58 34 63 41 63 50 '
        'C 63 56 60 60 58 62 L 58 70 L 42 70 L 42 62 '
        'C 40 60 37 56 37 50 C 37 41 42 34 50 34 Z"/>'
        '</g>'
        '<ellipse cx="45" cy="48" rx="3.2" ry="3.8" fill="#0c0e0a"/>'
        '<ellipse cx="55" cy="48" rx="3.2" ry="3.8" fill="#0c0e0a"/>'
        '<path d="M50 53 L48.5 57 L51.5 57 Z" fill="#0c0e0a"/>'
        '<rect x="44" y="64" width="1.3" height="5" fill="#0c0e0a"/>'
        '<rect x="47" y="64" width="1.3" height="5" fill="#0c0e0a"/>'
        '<rect x="50" y="64" width="1.3" height="5" fill="#0c0e0a"/>'
        '<rect x="53" y="64" width="1.3" height="5" fill="#0c0e0a"/>'
        '<rect x="56" y="64" width="1.3" height="5" fill="#0c0e0a"/>'
    )
    return _wrap(size, body)


def _tau(size: int) -> str:
    body = (
        '<circle cx="50" cy="50" r="42" fill="none" '
        'stroke="#c87f2a" stroke-width="2.6"/>'
        '<circle cx="50" cy="50" r="38" fill="none" '
        'stroke="#c87f2a" stroke-width="0.6"/>'
        '<path d="M50 20 L60 50 L50 80 L40 50 Z" '
        'fill="none" stroke="#e6a04a" stroke-width="3"/>'
        '<rect x="48.4" y="12" width="3.2" height="12" fill="#e6a04a"/>'
        '<polygon points="50,8 53,12 47,12" fill="#e6a04a"/>'
        '<rect x="38" y="48" width="24" height="4" fill="#e6a04a"/>'
        '<circle cx="50" cy="50" r="2.4" fill="#e6a04a"/>'
    )
    return _wrap(size, body)


def _eldar(size: int) -> str:
    # "Глаз Иши" — стилизованный эльдарский глаз со слезой.
    body = (
        '<g fill="#4ab8a8">'
        # Верхнее веко: толстая диагональная полоса
        '<path d="M 5 52 L 5 58 L 22 55 '
        'L 50 42 L 82 22 L 92 14 L 92 22 '
        'L 68 36 L 72 40 L 72 46 '
        'L 58 50 L 22 62 L 5 65 Z"/>'
        # Нижнее веко: дуга от левого угла до правого
        '<path d="M 22 62 Q 46 80 72 46 '
        'L 68 42 Q 46 72 26 58 Z"/>'
        # Радужка (полукруг)
        '<path d="M 38 52 A 12 12 0 0 1 62 52 '
        'L 62 50 L 38 50 Z"/>'
        # Ножка-хвост вниз
        '<path d="M 44 64 L 44 92 L 54 92 L 54 64 Z"/>'
        # Слеза
        '<path d="M 22 68 Q 16 82 16 88 '
        'Q 16 96 22 96 Q 28 96 28 88 '
        'Q 28 82 22 68 Z"/>'
        '</g>'
        # Зрачок — фон темы
        '<circle cx="50" cy="52" r="5" fill="#0a0e0e"/>'
    )
    return _wrap(size, body)


def _necrons(size: int) -> str:
    body = (
        '<path d="M50 10 L90 82 L10 82 Z" fill="none" '
        'stroke="#4ab84a" stroke-width="3"/>'
        '<path d="M50 22 L81 76 L19 76 Z" fill="none" '
        'stroke="#4ab84a" stroke-width="0.8"/>'
        '<path d="M50 34 L66 62 L34 62 Z" fill="#4ab84a"/>'
        '<ellipse cx="50" cy="54" rx="6" ry="3.2" fill="#0a050e"/>'
        '<circle cx="50" cy="54" r="1.4" fill="#7ae07a"/>'
        '<line x1="50" y1="10" x2="50" y2="2" stroke="#7ae07a" '
        'stroke-width="1.4"/>'
        '<line x1="4" y1="86" x2="96" y2="86" stroke="#4ab84a" '
        'stroke-width="1.4"/>'
    )
    return _wrap(size, body)


def _orks(size: int) -> str:
    body = (
        '<path d="M50 18 C 64 18 74 30 74 44 C 74 54 70 60 66 64 '
        'L 66 72 C 66 76 62 80 50 80 C 38 80 34 76 34 72 '
        'L 34 64 C 30 60 26 54 26 44 C 26 30 36 18 50 18 Z" '
        'fill="#7ac83a" stroke="#2a4a0e" stroke-width="1"/>'
        '<ellipse cx="41" cy="42" rx="4.2" ry="4.6" fill="#0e0a04"/>'
        '<ellipse cx="59" cy="42" rx="4.2" ry="4.6" fill="#0e0a04"/>'
        '<circle cx="41" cy="42" r="1.4" fill="#c8e878"/>'
        '<circle cx="59" cy="42" r="1.4" fill="#c8e878"/>'
        '<path d="M40 68 L42 78 L44 68 Z" fill="#f0e0a0"/>'
        '<path d="M46 68 L48 80 L50 68 Z" fill="#f0e0a0"/>'
        '<path d="M52 68 L54 80 L56 68 Z" fill="#f0e0a0"/>'
        '<path d="M58 68 L60 78 L62 68 Z" fill="#f0e0a0"/>'
        '<path d="M22 32 L14 24 L20 36 Z" fill="#7ac83a"/>'
        '<path d="M78 32 L86 24 L80 36 Z" fill="#7ac83a"/>'
    )
    return _wrap(size, body)


def _tyranids(size: int) -> str:
    body = (
        '<path d="M50 8 C 72 12 88 30 88 52 C 88 70 76 84 60 90 '
        'L 50 96 L 40 90 C 24 84 12 70 12 52 C 12 30 28 12 50 8 Z" '
        'fill="none" stroke="#b84ad0" stroke-width="3"/>'
        '<path d="M50 20 C 64 22 74 34 74 50 C 74 62 68 72 58 78 '
        'L 50 84 L 42 78 C 32 72 26 62 26 50 C 26 34 36 22 50 20 Z" '
        'fill="#8a2aa0" stroke="#b84ad0" stroke-width="0.8"/>'
        '<circle cx="38" cy="42" r="2.4" fill="#f0e0f0"/>'
        '<circle cx="44" cy="40" r="2.0" fill="#f0e0f0"/>'
        '<circle cx="50" cy="41" r="1.8" fill="#f0e0f0"/>'
        '<circle cx="62" cy="42" r="2.4" fill="#f0e0f0"/>'
        '<circle cx="56" cy="40" r="2.0" fill="#f0e0f0"/>'
        '<path d="M42 66 L32 88 L40 70 Z" fill="#b84ad0"/>'
        '<path d="M58 66 L68 88 L60 70 Z" fill="#b84ad0"/>'
        '<path d="M46 70 L50 88 L54 70 Z" fill="#b84ad0"/>'
        '<ellipse cx="50" cy="62" rx="5" ry="3.2" fill="#0a050e"/>'
    )
    return _wrap(size, body)


def _dark(size: int) -> str:
    body = (
        '<circle cx="50" cy="50" r="42" fill="none" stroke="#8b1a1a" '
        'stroke-width="1" opacity="0.4"/>'
        '<g fill="#b03030" stroke="#8b1a1a" stroke-width="1.2">'
        '<polygon points="50,14 68,50 50,86 32,50"/>'
        '<polygon points="50,26 60,50 50,74 40,50" fill="#0e0e10"/>'
        '<polygon points="50,34 55,50 50,66 45,50" fill="#b03030"/>'
        '</g>'
    )
    return _wrap(size, body)


_DISPATCH = {
    "dark": _dark,
    "imperial": _imperial,
    "mechanicum": _mechanicum,
    "chaos": _chaos,
    "imperial_guard": _imperial_guard,
    "tau": _tau,
    "eldar": _eldar,
    "necrons": _necrons,
    "orks": _orks,
    "tyranids": _tyranids,
}
"""


FILES["CHANGELOG.md"] = r"""# Changelog

Все значимые изменения проекта «Истории Кота Баюна».

## [1.0.5] — 2026-09-23

### Fixed

- **SVG-fallback Эльдар** заменён на «Глаз Иши» — стилизованный
  эльдарский глаз со слезой. Используется, когда `eldar.png`
  в `static/sigils/` отсутствует или повреждён.

## [1.0.4] — 2026-09-23

### Changed

- INITIATIO всегда после логина; символ mechanicum.
- Проверка сигнатуры PNG, расширенные логи `[assets]`.

## [1.0.3] — 2026-09-23

- Сиглы через SVG feColorMatrix (акцент темы, без фона).

## [1.0.2] — 2026-09-23

- Тема «Хаос» + 8-конечная звезда.

## [1.0.1] — 2026-09-23

- Сиглы из `static/sigils/`.
- Правовая плашка на splash.

## [1.0.0] — 2026-09-23

Первый полноценный релиз.
"""


def _write_one(rel_path: str, content: str) -> str:
    dst = ROOT / rel_path
    dst.parent.mkdir(parents=True, exist_ok=True)
    existed = dst.exists()
    if existed:
        try:
            old = dst.read_text(encoding="utf-8")
        except Exception as e:
            return "ERROR reading: " + type(e).__name__ + ": " + str(e)
        if old == content:
            return "skip (identical)"
    if dst.suffix == ".py":
        try:
            ast.parse(content)
        except SyntaxError as e:
            return ("ERROR SyntaxError: line " + str(e.lineno)
                    + ": " + str(e.msg))
    if existed:
        bak = dst.with_name(dst.name + ".bak_pre_" + TAG)
        try:
            shutil.copy2(dst, bak)
        except Exception as e:
            return "ERROR backup: " + type(e).__name__ + ": " + str(e)
    try:
        dst.write_text(content, encoding="utf-8")
    except Exception as e:
        return "ERROR write: " + type(e).__name__ + ": " + str(e)
    return "backup + overwrite" if existed else "create"


def main() -> int:
    print("=" * 64)
    print("PATCH " + TAG + " — fallback Эльдар: Глаз Иши")
    print("ROOT: " + str(ROOT))
    print("=" * 64)

    any_error = False
    for rel in FILES:
        status = _write_one(rel, FILES[rel])
        if status.startswith("ERROR"):
            any_error = True
        print("  " + rel.ljust(30) + " -> " + status)

    print("=" * 64)
    print("DONE" + (" (with errors)" if any_error else " — ok"))
    return 1 if any_error else 0


if __name__ == "__main__":
    sys.exit(main())