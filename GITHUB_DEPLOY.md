# Экспорт на GitHub — инструкция

## 1. Проверь `.gitignore`

В корне проекта уже должен быть `.gitignore` (PATCH_30 его дополнил).
Ключевое, что не должно попасть в репозиторий:

- `.env`, `.streamlit/secrets.toml` — секреты
- `data/users/*/` — персонажи и чаты игроков
- `data/users/*/autosave/` — автосейвы
- `chroma_db/` — большая база (сотни МБ)
- `data/_index.json` — пересоздаётся автоматически
- `*.bak_pre_*` — бэкапы патчей

## 2. Первый push (если репо ещё нет)

Открой github.com/new и создай **пустой** репозиторий (без README, без .gitignore).

Потом в CMD:

    cd /d C:\Users\79109\Desktop\Wh40K
    git init
    git branch -M main
    git add .
    git commit -m "Alpha build: WH40K RPG v0.1"
    git remote add origin https://github.com/ВАШ_НИК/ИМЯ_РЕПО.git
    git push -u origin main

## 3. Обновления

Каждый раз после изменений:

    cd /d C:\Users\79109\Desktop\Wh40K
    git add .
    git commit -m "краткое описание изменений"
    git push

## 4. Деплой на Streamlit Cloud

1. Зайди на share.streamlit.io, войди через GitHub.
2. Нажми Create app.
3. Repository: выбери свой репо.
4. Main file path: app.py.
5. Advanced settings → Secrets: вставь содержимое из `.streamlit/secrets.toml`.
6. Deploy.

## 5. Секреты для Streamlit Cloud

Streamlit Cloud → твоё приложение → Settings → Secrets:

    GIGACHAT_API_KEY = "твой_ключ_base64"
    GIGACHAT_SCOPE = "GIGACHAT_API_PERS"
    GIGACHAT_VERIFY_SSL = "0"

## 6. Если нужно запушить chroma_db

    git lfs install
    git lfs track "chroma_db/**"
    git add .gitattributes
    git add chroma_db
    git commit -m "Add chroma_db via LFS"
    git push
