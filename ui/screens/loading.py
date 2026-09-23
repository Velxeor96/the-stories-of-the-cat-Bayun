# PATCH_15T
# ui/screens/loading.py — INITIATIO. Символ — mechanicum (из static/sigils
# или встроенный fallback). Анимация: шестерня, прогресс, фразы.
from __future__ import annotations

import random
import time

import streamlit as st

from ui.assets import sigil_svg


LOADING_CSS = '''<style>
.load-wrap {
    display: flex; flex-direction: column;
    align-items: center; text-align: center;
    padding: 24px 20px 10px 20px;
    min-height: 62vh;
}
.cog-spin {
    width: 150px; height: 150px;
    color: var(--accent);
    filter: drop-shadow(0 0 26px var(--accent-glow));
    animation: cogSpin 9s linear infinite;
    margin-bottom: 4px;
    display: flex; align-items: center; justify-content: center;
}
.cog-spin svg, .cog-spin img { display: block; max-width: 100%; max-height: 100%; }
@keyframes cogSpin {
    from { transform: rotate(0deg); }
    to   { transform: rotate(360deg); }
}
.load-title {
    font-family: Georgia, serif;
    font-size: 28px; letter-spacing: 8px;
    color: var(--fg); margin: 10px 0 4px 0;
    text-shadow: 0 0 22px var(--accent-glow);
}
.load-sub {
    color: var(--fg-dim); font-style: italic;
    letter-spacing: 3px; font-size: 13px;
    margin-bottom: 22px;
}
.load-progress {
    width: 560px; max-width: 82vw;
    height: 8px;
    background: rgba(255,255,255,0.05);
    border: 1px solid var(--accent);
    border-radius: 4px;
    overflow: hidden;
    margin: 6px 0 22px 0;
}
.load-progress-fill {
    height: 100%;
    background: var(--accent);
    box-shadow: 0 0 12px var(--accent-glow);
    transition: width 0.18s linear;
}
.load-phrase {
    font-family: Consolas, 'Courier New', monospace;
    font-size: 14px;
    color: var(--fg);
    min-height: 26px;
    max-width: 640px;
    padding: 10px 20px;
    border-left: 2px solid var(--accent);
    background: rgba(255,255,255,0.03);
    text-align: left;
    letter-spacing: 0.4px;
}
.load-percent {
    font-family: Consolas, 'Courier New', monospace;
    color: var(--fg-dim);
    font-size: 12px; letter-spacing: 2px;
    margin-top: 12px;
}
</style>'''


PHRASES = [
    "Молита Омниссии. Установка священных баз знаний...",
    "Инициализация протоколов славления духов машины...",
    "Проверка целостности когитатора...",
    "Духи машины пробуждены. Приветствие адепта...",
    "Ритуал активации варп-приёмников...",
    "Сверка с архивом Марса...",
    "Активация первичной мнемо-матрицы...",
    "Калибровка ауспиков. Частота 0.314...",
    "Благословение святых реле...",
    "Загрузка литаний Омниссии...",
    "Окропление святой водой датчиков...",
    "Проверка ноосферного канала...",
    "Активация катушек Теслы...",
    "Разогрев гекс-терминалов...",
    "Очистка кэша от скверны...",
    "Синхронизация с машинным духом корабля...",
    "Освящение реле-станций...",
    "Проверка люминесцентных ламп...",
    "Инициализация мнемо-кода Терры...",
    "Проверка печатей чистоты...",
    "Ритуал пробуждения сланцевого разума...",
    "Воззвание к Омниссии...",
    "Сверка хронометров с Марсом...",
    "Активация геллер-поля...",
    "Калибровка серво-моторов...",
    "Молитва Первому Духу Машины...",
    "Загрузка Кодекса Механикум...",
    "Проверка родового герба династии...",
    "Инициализация порта 77-B...",
    "Приветствие адепта, изъявившего волю...",
    "Сверка с регистром Вольных Торговцев...",
    "Бинарная молитва: 01001111 01101101 01101110...",
    "Активация когитационных пластин...",
    "Проверка статуса лазерных батарей...",
    "Разогрев плазменного ядра...",
    "Инициализация протокола Око Терры...",
    "Сверка с архивом Сегментум Обскурус...",
    "Освящение клавиатур...",
    "Молитва Сангвинору...",
    "Проверка подписей адептов...",
    "Активация святых сервочерепов...",
    "Калибровка vox-канала...",
    "Инициализация мнемо-шкафа...",
    "Молитва Магосу Доминус...",
    "Освящение кремниевых душ...",
    "Сверка протоколов с Ковчегом Марса...",
    "Приветствие духа-покровителя...",
    "Обряд освящения транзисторов...",
    "Проверка печати Инквизиции...",
    "Инициализация протокола Красного Ключа...",
    "Активация варп-мембраны...",
    "Молитва Когитатору...",
    "Сверка с проповедями Фабрикатора-Генерала...",
    "Освящение кристаллических линз...",
    "Пробуждение Омниссии в коде...",
    "Помазание святым маслом шестерён...",
    "Призывание духа-хранителя мнемо-куба...",
    "Сверка гексаграмм с эталоном Марса...",
    "Очистка мыслей от плотских сомнений...",
    "Проверка числа пи на святость...",
    "Ритуал перезаписи памяти...",
    "Сверка с писаниями Магоса-Верховного...",
    "Взывание к Отцу-Машине...",
    "Активация первичного когитатора...",
    "Прогрев термоядерного сердца...",
    "Молитва о защите от Скверны...",
    "Освящение шины данных...",
    "Проверка отпечатков биометрии адепта...",
    "Заряд святых аккумуляторов...",
    "Воззвание к Духу Святому Машины...",
    "Бинарное славословие: 01000010 01101100...",
    "Инициализация гексаграмм Терры...",
    "Проверка кабеля номер 7B-3A...",
    "Активация сигила Механикум...",
    "Освящение катода и анода...",
    "Сверка с реестром адептов...",
    "Молитва Ковчегу Марса...",
    "Загрузка литании Освобождения...",
    "Активация протокола Благословения...",
    "Приветствие Первого Адепта...",
    "Сверка координат с Священной Террой...",
    "Калибровка гекс-гармоник...",
    "Молитва о ниспослании Мудрости...",
    "Пробуждение спящего духа машины...",
    "Ритуал сожжения еретических данных...",
    "Проверка подлинности печати Инквизитора...",
    "Призывание духа Рода Баюна...",
    "Сверка родословной династии...",
    "Освящение антенны дальней связи...",
    "Активация канала Астропата...",
    "Проверка силы сигнала Варпа...",
    "Молитва о крепком геллер-поле...",
    "Приветствие свету Императора...",
    "Загрузка хроник Эры Раздора...",
    "Сверка с писаниями Экклезиархии...",
    "Взывание к Кодексу Астартес...",
    "Освящение геносемени...",
    "Пробуждение Омниссии в жилах...",
    "Адептус Механикус. Дух жив. Дух вечен...",
    "Славься Машина. Славься Омниссия...",
]


def _cog() -> str:
    try:
        svg = sigil_svg("mechanicum", 140)
    except Exception as e:
        print("[loading] sigil fail: "
              + type(e).__name__ + ": " + str(e))
        svg = ""
    return "<div class='cog-spin'>" + svg + "</div>"


def _html(progress, phrase):
    return (
        "<div class='load-wrap'>"
        + _cog()
        + "<div class='load-title'>INITIATIO</div>"
        + "<div class='load-sub'>дух-машины пробуждается</div>"
        + "<div class='load-progress'>"
        + "<div class='load-progress-fill' style='width: "
        + str(progress) + "%;'></div>"
        + "</div>"
        + "<div class='load-phrase'>" + phrase + "</div>"
        + "<div class='load-percent'>[ " + str(progress) + "% ]</div>"
        + "</div>"
    )


def _finish():
    login = st.session_state.get("user_login")
    if login:
        try:
            from persistence.settings import set_setting
            set_setting(login, "loading_seen", True)
        except Exception as e:
            print("[loading] set_setting fail: "
                  + type(e).__name__ + ": " + str(e))
    st.session_state["_loading_anim_done"] = False
    st.session_state.screen = "main_menu"
    st.rerun()


def _run_animation():
    placeholder = st.empty()
    pool = list(PHRASES)
    random.shuffle(pool)

    total_steps = 100
    dt = 0.1
    elapsed = 0.0
    phrase_idx = 0
    next_phrase_at = 0.0
    current = pool[0]

    for step in range(total_steps + 1):
        progress = int(step / total_steps * 100)
        if elapsed >= next_phrase_at:
            current = pool[phrase_idx % len(pool)]
            phrase_idx += 1
            next_phrase_at = elapsed + random.uniform(3.0, 5.0)
        placeholder.markdown(_html(progress, current),
                             unsafe_allow_html=True)
        time.sleep(dt)
        elapsed += dt

    st.session_state["_loading_anim_done"] = True
    st.rerun()


def render():
    st.markdown(LOADING_CSS, unsafe_allow_html=True)
    login = st.session_state.get("user_login")
    if not login:
        st.warning("Нет активной сессии.")
        if st.button("На главную", key="loading_nologin"):
            st.session_state.screen = "splash"
            st.rerun()
        return

    if st.session_state.get("_loading_anim_done"):
        st.markdown(_html(100, "> ДУХ-МАШИНЫ ГОТОВ К СЛУЖЕНИЮ."),
                    unsafe_allow_html=True)
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            if st.button("Продолжить", use_container_width=True,
                         type="primary", key="loading_continue"):
                _finish()
        return

    _run_animation()
