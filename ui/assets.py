# PATCH_11_THEME_ALL_V2
'''ui/assets.py — SVG-логотипы для тем.'''
from __future__ import annotations


def sigil_svg(theme: str = "dark", size: int = 96) -> str:
    '''Герб-логотип темы.'''
    if theme == "imperial":
        return _imperial(size)
    if theme == "mechanicum":
        return _mechanicum(size)
    return _dark(size)


def _imperial(size: int) -> str:
    return (
        '<svg width="' + str(size) + '" height="' + str(size) + '" '
        'viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">'
        '<defs>'
        '<radialGradient id="g_i" cx="50%" cy="50%" r="60%">'
        '<stop offset="0%" stop-color="#d4a017" stop-opacity="0.9"/>'
        '<stop offset="100%" stop-color="#b8860b" stop-opacity="0.2"/>'
        '</radialGradient>'
        '<filter id="f_i" x="-50%" y="-50%" width="200%" height="200%">'
        '<feGaussianBlur stdDeviation="2" result="b"/>'
        '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>'
        '</filter>'
        '</defs>'
        '<circle cx="50" cy="50" r="42" fill="none" stroke="#b8860b" '
        'stroke-width="1" opacity="0.4"/>'
        '<g filter="url(#f_i)" fill="url(#g_i)" stroke="#d4a017" stroke-width="0.8">'
        '<path d="M50 20 L50 80 M30 35 L50 45 L70 35 '
        'M25 50 L50 55 L75 50 M22 65 L50 62 L78 65" '
        'stroke-width="1.2" fill="none"/>'
        '<path d="M50 22 C 40 26 35 30 30 35 C 38 34 46 30 50 26 '
        'C 54 30 62 34 70 35 C 65 30 60 26 50 22 Z"/>'
        '<path d="M50 78 C 42 76 36 72 30 66 C 36 68 44 72 50 76 '
        'C 56 72 64 68 70 66 C 64 72 58 76 50 78 Z"/>'
        '<circle cx="50" cy="50" r="4" fill="#d4a017"/>'
        '</g>'
        '</svg>'
    )


def _mechanicum(size: int) -> str:
    return (
        '<svg width="' + str(size) + '" height="' + str(size) + '" '
        'viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">'
        '<defs>'
        '<radialGradient id="g_m" cx="50%" cy="50%" r="60%">'
        '<stop offset="0%" stop-color="#c83838" stop-opacity="0.9"/>'
        '<stop offset="100%" stop-color="#a02020" stop-opacity="0.2"/>'
        '</radialGradient>'
        '<filter id="f_m" x="-50%" y="-50%" width="200%" height="200%">'
        '<feGaussianBlur stdDeviation="2" result="b"/>'
        '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>'
        '</filter>'
        '</defs>'
        '<circle cx="50" cy="50" r="42" fill="none" stroke="#a02020" '
        'stroke-width="1" opacity="0.4"/>'
        '<g filter="url(#f_m)" stroke="#c83838" stroke-width="1.2" fill="none">'
        '<circle cx="50" cy="50" r="20"/>'
        '<circle cx="50" cy="50" r="12"/>'
        '<circle cx="50" cy="50" r="4" fill="#c83838"/>'
        '<g stroke-width="2">'
        '<path d="M50 18 L50 28 M50 72 L50 82 M18 50 L28 50 M72 50 L82 50 '
        'M27 27 L34 34 M66 66 L73 73 M27 73 L34 66 M66 34 L73 27"/>'
        '</g>'
        '</g>'
        '<circle cx="50" cy="50" r="26" fill="none" stroke="#c83838" '
        'stroke-width="0.6" stroke-dasharray="2 4"/>'
        '</svg>'
    )


def _dark(size: int) -> str:
    return (
        '<svg width="' + str(size) + '" height="' + str(size) + '" '
        'viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">'
        '<defs>'
        '<radialGradient id="g_d" cx="50%" cy="50%" r="60%">'
        '<stop offset="0%" stop-color="#b03030" stop-opacity="0.9"/>'
        '<stop offset="100%" stop-color="#8b1a1a" stop-opacity="0.2"/>'
        '</radialGradient>'
        '<filter id="f_d" x="-50%" y="-50%" width="200%" height="200%">'
        '<feGaussianBlur stdDeviation="2" result="b"/>'
        '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>'
        '</filter>'
        '</defs>'
        '<circle cx="50" cy="50" r="42" fill="none" stroke="#8b1a1a" '
        'stroke-width="1" opacity="0.4"/>'
        '<g filter="url(#f_d)" fill="url(#g_d)" stroke="#b03030" stroke-width="1.2">'
        '<polygon points="50,14 68,50 50,86 32,50"/>'
        '<polygon points="50,26 60,50 50,74 40,50" fill="#0e0e10"/>'
        '<polygon points="50,34 55,50 50,66 45,50" fill="#b03030"/>'
        '</g>'
        '</svg>'
    )
