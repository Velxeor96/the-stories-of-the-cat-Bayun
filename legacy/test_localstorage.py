# test_localstorage.py
# Мини-тест: работает ли localStorage на Streamlit Cloud.
import streamlit as st

try:
    from streamlit_local_storage import LocalStorage
    HAS_LS = True
except Exception as e:
    HAS_LS = False
    st.error(f"Импорт упал: {e}")


st.title("🧪 Тест localStorage")

if not HAS_LS:
    st.stop()

localS = LocalStorage()

st.write("Введи что-нибудь. Значение сохранится в localStorage браузера.")
test_value = st.text_input("Значение", value="")

col1, col2 = st.columns(2)
with col1:
    if st.button("💾 Сохранить"):
        localS.setItem("test_key", test_value)
        st.success(f"Сохранено: {test_value}")

with col2:
    if st.button("📖 Прочитать"):
        result = localS.getItem("test_key")
        st.info(f"Из localStorage: {result}")

st.write("---")
st.write("**Инструкция:**")
st.write("1. Введи слово → Сохранить.")
st.write("2. Перезагрузи страницу (F5).")
st.write("3. Нажми Прочитать → должно показать твоё слово.")
st.write("4. Если показало — localStorage работает.")