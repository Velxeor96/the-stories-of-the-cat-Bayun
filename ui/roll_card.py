# PATCH_15Z
# ui/roll_card.py — карточка броска d100 в стиле активной темы.
# Две формы:
#   fresh=True  — большая карточка после свежего броска
#   fresh=False — компактная строка для истории чата
from __future__ import annotations

import streamlit as st

from ui.loading_screen import inline_html


# Титулы по темам. Ключ темы -> (успех, провал, крит.успех, крит.провал)
TITLES = {
    "dark":           ("УСПЕХ", "ПРОВАЛ", "ЗНАМЕНИЕ", "КАТАСТРОФА"),
    "imperial":       ("СВЕРШИЛОСЬ", "ИМПЕРАТОР НЕ ЗАЩИТИЛ",
                       "ВОЛЯ ИМПЕРАТОРА", "КАРА ИМПЕРАТОРА"),
    "mechanicum":     ("[ OK ]", "[ FAIL ]",
                       "МАШИНА БЛАГОСЛОВЛЯЕТ", "ШЕСТЕРНИ СКРИПЯТ"),
    "chaos":          ("ДАР БОГОВ", "ОТВЕРГНУТО",
                       "СЛАВА ХАОСУ", "ЦЕНА КРОВИ"),
    "imperial_guard": ("СЛУЖУ ИМПЕРАТОРУ", "ПРИКАЗ НЕ ВЫПОЛНЕН",
                       "ИМПЕРАТОР ЗАЩИЩАЕТ", "ЦЕНОЙ ЖИЗНЕЙ"),
    "tau":            ("СЛУЖУ ВЫСШЕМУ БЛАГУ", "НЕ ВО ИМЯ БЛАГА",
                       "СОВЕРШЕНСТВО КАСТЫ", "ПУТЬ ПОТЕРЯН"),
    "eldar":          ("ПУТЬ ОТКРЫТ", "ЗАПУТАЛИСЬ",
                       "НИТИ СУДЬБЫ СПЛЕЛИСЬ", "РОК"),
    "necrons":        ("ПРОТОКОЛ", "СБОЙ",
                       "ИДЕАЛЬНО", "ФАТАЛЬНАЯ ОШИБКА"),
    "orks":           ("ДА, БОСС!", "НЕ ПРЁТ",
                       "ВАААГХ!", "ХРЕНА С ДВА!"),
    "tyranids":       ("ОДОБРЕНО УЛЬЕМ", "ЖЕРТВА",
                       "СВЕРХРАЗУМ ДОВОЛЕН", "ОТТОРГНУТО"),
    "tzeench":        ("СЛАВА ТЗИНЧУ!", "СУДЬБА ОБОРВАЛАСЬ",
                       "ВЕЛИКИЙ ЗАМЫСЕЛ", "ТЗИНЧ СМЕЁТСЯ"),
    "khorn":          ("КРОВЬ!", "СЛАБО",
                       "КРОВАВАЯ ЖАТВА", "НЕДОСТОИН ЯРОСТИ"),
    "noorgl":         ("ДЕД ДОВОЛЕН", "НЕ ПРИНЯТ",
                       "ВЕЛИКИЙ ДАР", "ГНИЛЬ"),
    "slaanesh":       ("УСЛАДА", "ПРЕСНО",
                       "ЭКСТАЗ", "ИЗЫСКАННАЯ БОЛЬ"),
    "inquisition":    ("ОДОБРЕНО", "ОТКЛОНЕНО",
                       "ПЕЧАТЬ ИМПЕРАТОРА", "ЕРЕСЬ"),
    "gidra":          ("ЭТО БЫЛО СЛИШКОМ ПРОСТО", "СЕТЬ ДЕМАСКИРОВАНА",
                       "HYDRA DOMINATUS!", "ПРОВАЛ ЛЕГИОНА"),
}


_CARD_CSS = '''<style>
@keyframes rcPulse {
    0%, 100% { box-shadow: 0 0 24px var(--rc-glow), 0 0 48px var(--rc-glow),
                           0 6px 20px var(--shadow); }
    50%      { box-shadow: 0 0 40px var(--rc-glow), 0 0 80px var(--rc-glow),
                           0 6px 20px var(--shadow); }
}
@keyframes rcFlicker {
    0%, 100% { opacity: 1; }
    45%      { opacity: 0.92; }
    50%      { opacity: 0.7; }
    55%      { opacity: 0.92; }
}
@keyframes rcBreathe {
    0%, 100% { transform: scale(1); }
    50%      { transform: scale(1.012); }
}
@keyframes rcScan {
    0%   { background-position: -100% 0; }
    100% { background-position: 200% 0; }
}
.rc-fresh {
    max-width: 560px;
    margin: 18px auto 22px auto;
    padding: 22px 26px 20px 26px;
    border: 2px solid var(--rc-color);
    border-radius: 14px;
    background: linear-gradient(180deg,
        color-mix(in srgb, var(--rc-color) 8%, var(--panel)) 0%,
        var(--panel) 100%);
    text-align: center;
    position: relative;
    overflow: hidden;
    animation: rcPulse 2.4s ease-in-out infinite,
               rcBreathe 5s ease-in-out infinite;
}
.rc-fresh.rc-flicker { animation: rcPulse 2.4s ease-in-out infinite,
                                   rcFlicker 3.5s ease-in-out infinite; }
.rc-scanline {
    position: absolute; top: 0; left: 0; right: 0; height: 2px;
    background: linear-gradient(90deg, transparent 0%,
        var(--rc-color) 50%, transparent 100%);
    background-size: 200% 100%;
    animation: rcScan 3s linear infinite;
}
.rc-skill {
    font-family: Georgia, serif;
    font-size: 15px; letter-spacing: 2px;
    color: var(--fg-dim); text-transform: uppercase;
}
.rc-diff {
    font-size: 12px; color: var(--fg-dim);
    letter-spacing: 1px; margin-top: 4px;
}
.rc-number {
    font-family: Georgia, serif;
    font-size: 68px;
    font-weight: bold;
    line-height: 1;
    color: var(--rc-color);
    text-shadow: 0 0 20px var(--rc-glow),
                 0 0 40px var(--rc-glow),
                 0 0 60px var(--rc-glow);
    margin: 18px 0 4px 0;
}
.rc-vs {
    font-size: 12px; color: var(--fg-dim);
    letter-spacing: 1px;
    margin-bottom: 16px;
}
.rc-title {
    font-family: Georgia, serif;
    font-size: 22px;
    letter-spacing: 6px;
    color: var(--rc-color);
    text-shadow: 0 0 18px var(--rc-glow);
    padding: 8px 0 4px 0;
    border-top: 1px solid var(--rc-color);
    border-bottom: 1px solid var(--rc-color);
    margin: 6px 0 12px 0;
}
.rc-degrees {
    font-size: 13px; color: var(--fg-dim);
    letter-spacing: 1px;
}
.rc-compact {
    display: block;
    padding: 6px 12px;
    margin: 6px 0;
    border-left: 3px solid var(--rc-color);
    background: rgba(255,255,255,0.025);
    border-radius: 4px;
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 12px;
    color: var(--fg);
}
.rc-compact .rc-ct {
    font-weight: bold;
    color: var(--rc-color);
    letter-spacing: 1px;
}
.rc-compact .rc-cd { color: var(--fg-dim); }
.rc-spinner {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 22px 0 16px 0;
}
.rc-spinner .rc-cog {
    width: 96px; height: 96px;
    animation: rcSpin 6s linear infinite;
    filter: drop-shadow(0 0 18px var(--accent-glow));
    display: flex; align-items: center; justify-content: center;
}
.rc-spinner .rc-cog svg, .rc-spinner .rc-cog img {
    display: block; max-width: 100%; max-height: 100%;
}
@keyframes rcSpin {
    from { transform: rotate(0deg); }
    to   { transform: rotate(360deg); }
}
.rc-spinner .rc-label {
    margin-top: 14px;
    font-family: Consolas, 'Courier New', monospace;
    font-size: 13px; letter-spacing: 3px;
    color: var(--accent);
    text-transform: uppercase;
}
.rc-spinner .rc-sub {
    margin-top: 4px;
    font-size: 11px; color: var(--fg-dim);
    font-style: italic;
}
</style>'''


def _theme():
    try:
        from ui.theme import _current
        return _current()
    except Exception:
        return "dark"


def _titles(theme):
    return TITLES.get(theme, TITLES["dark"])


def _color_and_class(roll):
    success = bool(roll.get("success"))
    crit_s = bool(roll.get("crit_success")) or roll.get("critical") == "success"
    crit_f = bool(roll.get("crit_fail")) or roll.get("critical") == "fail"
    if crit_s:
        return "#FFD700", "rc-crit-success", "crit_success"
    if crit_f:
        return "#8B0000", "rc-crit-fail", "crit_fail"
    if success:
        return "#2E7D32", "rc-success", "success"
    return "#B71C1C", "rc-fail", "fail"


def _short_diff(d):
    return {
        "Trivial": "Тривиальная (+60)",
        "Easy": "Лёгкая (+30)",
        "Routine": "Рутинная (+20)",
        "Ordinary": "Обычная (+10)",
        "Challenging": "Вызов (0)",
        "Difficult": "Трудная (-10)",
        "Hard": "Тяжёлая (-20)",
        "Very Hard": "Очень тяжёлая (-30)",
        "Hellish": "Адская (-60)",
    }.get(str(d), str(d))


def _degrees_line(roll):
    d = int(roll.get("degrees", 0) or 0)
    if d == 0:
        return "Без степени"
    if roll.get("success"):
        return "Степень успеха: " + str(d)
    return "Степень провала: " + str(d)




_DIALOG_CSS = '''<style>
.rd-wrap { display: flex; flex-direction: column;
    align-items: center; text-align: center;
    padding: 10px 0 8px 0; font-family: Georgia, serif; }
.rd-label {
    font-size: 11px; letter-spacing: 4px;
    color: var(--accent); text-transform: uppercase;
    margin-bottom: 6px; }
.rd-skill {
    font-family: Georgia, serif;
    font-size: 28px; letter-spacing: 5px;
    color: var(--accent-soft);
    text-shadow: 0 0 20px var(--accent-glow),
                 0 0 40px var(--accent-glow);
    text-transform: uppercase;
    margin: 8px 0 6px 0; }
.rd-diff {
    font-size: 13px; color: var(--fg-dim);
    letter-spacing: 2px; margin-bottom: 14px; }
.rd-target {
    font-size: 15px; color: var(--fg);
    margin-bottom: 26px; }
.rd-target b {
    color: var(--accent); font-size: 22px;
    text-shadow: 0 0 14px var(--accent-glow); }
.rd-die {
    font-family: Georgia, serif;
    font-size: 112px; font-weight: bold; line-height: 1;
    color: var(--accent);
    text-shadow:
        0 0 20px var(--accent-glow),
        0 0 40px var(--accent-glow),
        0 0 80px var(--accent-glow);
    margin: 20px 0 10px 0;
    animation: rdShake 0.14s linear infinite; }
@keyframes rdShake {
    0%   { transform: translate(0, 0) rotate(0deg); }
    25%  { transform: translate(-2px, 1px) rotate(-0.8deg); }
    50%  { transform: translate(1px, -2px) rotate(0.6deg); }
    75%  { transform: translate(-1px, 2px) rotate(-0.4deg); }
    100% { transform: translate(2px, -1px) rotate(0.8deg); }
}
.rd-rolling {
    font-family: Consolas, "Courier New", monospace;
    font-size: 12px; letter-spacing: 3px;
    color: var(--accent); text-transform: uppercase;
    margin-top: 10px; }
.rd-hint {
    font-size: 11px; color: var(--fg-dim);
    font-style: italic; margin-top: 14px; }
</style>'''


def render_dialog_await(command_info):
    st.markdown(_DIALOG_CSS, unsafe_allow_html=True)
    skill = skill_ru(command_info.get("skill") or "Проверка")
    diff = _short_diff(command_info.get("difficulty", "Ordinary"))
    target = command_info.get("target", "?")
    html = (
        "<div class='rd-wrap'>"
        "<div class='rd-label'>Проверка</div>"
        "<div class='rd-skill'>" + skill + "</div>"
        "<div class='rd-diff'>" + diff + "</div>"
        "<div class='rd-target'>Порог: <b>" + str(target)
        + "</b></div>"
        "<div class='rd-hint'>Дух-машины ждут решения адепта.</div>"
        "</div>"
    )
    st.markdown(html, unsafe_allow_html=True)


def render_dialog_rolling(n):
    html = (
        "<div class='rd-wrap'>"
        "<div class='rd-die'>" + str(n) + "</div>"
        "<div class='rd-rolling'>дух-машины бросают кости</div>"
        "</div>"
    )
    st.markdown(_DIALOG_CSS + html, unsafe_allow_html=True)




SKILL_NAMES_RU = {
    'WS': 'Рукопашный бой',
    'BS': 'Стрельба',
    'S': 'Сила',
    'T': 'Стойкость',
    'Ag': 'Ловкость',
    'Int': 'Интеллект',
    'Per': 'Восприятие',
    'WP': 'Воля',
    'Fel': 'Общительность',
    'Awareness': 'Внимание',
    'Perception': 'Восприятие',
    'Charm': 'Убеждение',
    'Command': 'Командование',
    'Intimidate': 'Запугивание',
    'Melee': 'Рукопашный бой',
    'Dodge': 'Уклонение',
    'Pilot': 'Пилотирование',
    'Logic': 'Логика',
    'Medicae': 'Медицина',
    'Inquiry': 'Сбор информации',
    'Scrutiny': 'Дознание',
    'Tech-Use': 'Техноиспользование',
    'Common Lore': 'Общие знания',
}

def skill_ru(name):
    if not name:
        return 'Проверка'
    s = str(name)
    return SKILL_NAMES_RU.get(s, s)


def render_roll_card(roll, fresh=False):
    if not roll:
        return

    theme = _theme()
    t_succ, t_fail, t_cs, t_cf = _titles(theme)

    color, cls, kind = _color_and_class(roll)
    if kind == "crit_success":
        title = t_cs
    elif kind == "crit_fail":
        title = t_cf
    elif kind == "success":
        title = t_succ
    else:
        title = t_fail

    d100 = roll.get("roll", roll.get("d100", "?"))
    target = roll.get("target", "?")
    diff = _short_diff(roll.get("difficulty", "Ordinary"))
    reason = skill_ru(roll.get("reason", "") or "Проверка")
    degrees = _degrees_line(roll)

    st.markdown(_CARD_CSS, unsafe_allow_html=True)

    if fresh:
        glow = color + "55"
        flicker = " rc-flicker" if theme in (
            "chaos", "tzeench", "slaanesh", "inquisition"
        ) else ""
        scanline = "<div class='rc-scanline'></div>" if theme in (
            "necrons", "gidra", "mechanicum"
        ) else ""
        html = (
            "<div class='rc-fresh" + flicker + "' "
            "style='--rc-color: " + color + "; --rc-glow: " + glow + ";'>"
            + scanline
            + "<div class='rc-skill'>" + str(reason) + "</div>"
            + "<div class='rc-diff'>" + diff + "</div>"
            + "<div class='rc-number'>" + str(d100) + "</div>"
            + "<div class='rc-vs'>против порога " + str(target) + "</div>"
            + "<div class='rc-title'>" + title + "</div>"
            + "<div class='rc-degrees'>" + degrees + "</div>"
            + "</div>"
        )
        st.markdown(html, unsafe_allow_html=True)
        return

    # Компактная строка для истории
    html = (
        "<div class='rc-compact' style='--rc-color: " + color + ";'>"
        "<span class='rc-ct'>" + title + "</span> "
        "<span class='rc-cd'>·</span> "
        + skill_ru(reason)
        + " <span class='rc-cd'>· " + diff + "</span> "
        + "<span class='rc-cd'>· d100=" + str(d100)
        + " / " + str(target) + "</span> "
        + "<span class='rc-cd'>· " + degrees + "</span>"
        + "</div>"
    )
    st.markdown(html, unsafe_allow_html=True)


def render_spinner_html() -> str:
    theme = _theme()
    return inline_html(theme)
