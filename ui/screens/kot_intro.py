# PATCH_11_THEME_ALL_V2
'''ui/screens/kot_intro.py — вступительное слово Кота Баюна.'''
from __future__ import annotations

import streamlit as st

from persistence.settings import set_setting
from ui.assets import sigil_svg
from ui.theme import _current


KOT_CSS = '''<style>
.kot-wrap { max-width: 860px; margin: 24px auto; padding: 0 20px; }
.kot-hero {
    text-align: center; padding: 18px 0 6px 0;
    animation: fadeInUp 0.7s ease-out;
}
.kot-title {
    font-family: Georgia, serif; font-size: 42px;
    color: var(--accent-soft); text-align: center;
    margin: 12px 0 4px 0; letter-spacing: 4px;
    text-shadow: 0 0 24px var(--accent-glow);
}
.kot-sub {
    text-align: center; color: var(--fg-dim);
    font-style: italic; margin-bottom: 24px;
    font-size: 13px; letter-spacing: 2px;
}
.kot-scroll {
    background: linear-gradient(180deg, var(--panel-hi) 0%, var(--bg) 100%);
    border: 1px solid var(--border-hi);
    border-radius: 14px;
    padding: 32px 38px;
    box-shadow: 0 10px 44px var(--shadow),
                inset 0 0 80px var(--accent-glow);
    color: var(--fg);
    font-family: Georgia, 'Times New Roman', serif;
    line-height: 1.85;
    font-size: 15.5px;
    position: relative;
    animation: fadeInUp 0.9s ease-out;
}
.kot-scroll::before, .kot-scroll::after {
    content: '';
    position: absolute; left: 20px; right: 20px; height: 2px;
    background: linear-gradient(90deg, transparent 0%,
        var(--accent) 50%, transparent 100%);
    opacity: 0.7;
}
.kot-scroll::before { top: 0; }
.kot-scroll::after { bottom: 0; }
.kot-scroll p { margin: 0 0 18px 0; }
.kot-scroll .sig {
    text-align: right; color: var(--accent-soft);
    font-style: italic; margin-top: 28px;
    font-size: 17px; line-height: 1.5;
}
.kot-ornament {
    text-align: center; color: var(--accent);
    letter-spacing: 14px; font-size: 16px;
    margin: 26px 0 14px 0; opacity: 0.7;
}
</style>'''


KOT_HTML = '''<div class='kot-scroll'>
<p>Приветствую тебя, путник, зашедший на огонек в мою скромную обитель! Спасибо, что открыл ссылку и решил взглянуть на то, что мы тут ваяем. Это дорогого стоит, и я, Кот Баюн, это очень ценю. Устраивайся поудобнее, сейчас я расскажу тебе сказку о том, как рождается игра.</p>

<p>Разработка игр — это, скажу я тебе, ад кромешный. Это бесконечный круговорот багов, вылетов, неработающих скриптов и бессонных ночей. Особенно когда ты делаешь текстовую РПГ и не можешь свалить все косяки на плохую графику или кривые текстуры. Ты сидишь в три часа ночи, смотришь, как нейросеть выдает «планету Новый Иерусалим» в мрачном будущем, и думаешь: «Господи, за что?». Это выматывает, высасывает все соки и заставляет сомневаться во всем. Но... черт возьми, это безумно весело! Видеть, как из хаоса кода рождается что-то живое, как мир обретает очертания, а ИИ-Мастер перестает нести чушь и начинает вести историю — это магия, ради которой мы и терпим этот ад.</p>

<p>Мы пережили глобальную перестройку. Выкинули старую кашу из кода, заново собрали движок. Теперь Мастер не выдумывает локации, броски кубиков считает Python (а не нейросеть), а весь лор разложен по полочкам. Мы заставили эту махину работать как надо.</p>

<p>Но, как говорится, один в поле не воин. И в этом аду кромешном без надежного плеча рядом можно просто сойти с ума. Поэтому я хочу сказать огромное, искреннее спасибо тем, без кого этого проекта просто не существовало бы. В первую очередь — Ксении (ака Заяц). Заяц, да, это про тебя! Спасибо тебе огромное за то, что терпела меня все это время. За твое бесконечное терпение, за поддержку, за то, что не дала мне бросить это гиблое дело, когда руки опускались. Ты — мой самый главный критик и самый верный союзник. Без тебя этого проекта бы просто не было.</p>

<p>Отдельное спасибо всем, кто участвовал в альфа-тестах, ловил баги и не послал меня далеко и надолго. Раньше я перечислял вас тут, но теперь у нас есть целый экран «Создатели». Загляните туда, вы там есть. Вы все — настоящие герои, которые помогли сделать эту версию лучше.</p>

<p>Что дальше? Мы не стоим на месте. Сейчас мы доводим до ума Империум. Когда это ядро будет работать как швейцарские часы — мы откроем следующую фракцию. Это будет как DLC. Сначала одна идеальная, потом вторая. В планах — мобильная версия (чтобы играть с телефона) и нормальные космические бои. Впереди еще много работы, но мы движемся вперед.</p>

<p>Спасибо, что играли. Спасибо за вашу поддержку. Спасибо, что тратите свое время на наше творчество. Надеемся, вам понравилось. Если нет — пишите, мы всегда открыты для фидбека.</p>

<div class='sig'>С любовью и уважением,<br>Ваш Кот Баюн.</div>
</div>'''


def render() -> None:
    _css_ok = False
    try:
        st.html(KOT_CSS)
        _css_ok = True
    except Exception:
        st.markdown(KOT_CSS, unsafe_allow_html=True)
        _css_ok = True
    if not _css_ok:
        print("[kot_intro] css inject failed")
    theme = _current()
    sigil = sigil_svg(theme, size=80)

    st.markdown(
        f"<div class='kot-wrap'><div class='kot-hero'>{sigil}"
        "<div class='kot-title'>Кот Баюн</div>"
        "<div class='kot-sub'>вступительное слово</div>"
        f"</div>{KOT_HTML}</div>",
        unsafe_allow_html=True,
    )
    st.markdown("<div class='kot-ornament'>❦ ❦ ❦</div>",
                unsafe_allow_html=True)

    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        if st.button("Продолжить  →", width="stretch",
                     type="primary", key="kot_continue"):
            login = st.session_state.get("user_login")
            if login:
                try:
                    set_setting(login, "kot_intro_seen", True)
                except Exception as e:
                    print(f"[kot_intro] set_setting: {e}")
            st.session_state.screen = "loading"
            st.rerun()
