# scripts/collect_migration.ps1
# Собирает всё, что не в Git, в один архив для переноса

$ErrorActionPreference = "Stop"

# Корень проекта — определи автоматически
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

# Куда положить архив
$OutDir = "$env:USERPROFILE\Desktop"
$Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$ZipPath = "$OutDir\Wh40K_migration_$Stamp.zip"

Write-Host "=== Сбор миграционного пакета ===" -ForegroundColor Cyan
Write-Host "Источник: $Root"
Write-Host "Назначение: $ZipPath"
Write-Host ""

# Временная папка
$Temp = "$env:TEMP\wh40k_migration_$Stamp"
New-Item -ItemType Directory -Path $Temp -Force | Out-Null

# 1. ChromaDB
if (Test-Path "$Root\chroma_db") {
    Write-Host "[1/6] chroma_db..." -ForegroundColor Yellow
    Copy-Item "$Root\chroma_db" -Destination "$Temp\chroma_db" -Recurse
} else {
    Write-Host "[1/6] chroma_db НЕ найден — пропускаю" -ForegroundColor DarkYellow
}

# 2. Секреты
Write-Host "[2/6] Секреты..." -ForegroundColor Yellow
New-Item -ItemType Directory -Path "$Temp\.streamlit" -Force | Out-Null
$secrets_found = $false
foreach ($f in @(".streamlit\secrets.toml", "gigachat_key.txt", ".env")) {
    if (Test-Path "$Root\$f") {
        Copy-Item "$Root\$f" -Destination "$Temp\$f" -Force
        Write-Host "  + $f"
        $secrets_found = $true
    }
}
if (-not $secrets_found) {
    Write-Host "  Секреты не найдены!" -ForegroundColor Red
}

# 3. data/users
Write-Host "[3/6] data/users..." -ForegroundColor Yellow
if (Test-Path "$Root\data\users") {
    Copy-Item "$Root\data\users" -Destination "$Temp\data\users" -Recurse
    $user_count = (Get-ChildItem "$Root\data\users" -Directory).Count
    Write-Host "  Пользователей: $user_count"
} else {
    Write-Host "  data/users пуст" -ForegroundColor DarkYellow
}

# 4. config.yaml
Write-Host "[4/6] config.yaml..." -ForegroundColor Yellow
if (Test-Path "$Root\config.yaml") {
    Copy-Item "$Root\config.yaml" -Destination "$Temp\config.yaml"
}

# 5. VERSION + CHANGELOG
Write-Host "[5/6] VERSION + CHANGELOG..." -ForegroundColor Yellow
foreach ($f in @("VERSION", "CHANGELOG.md")) {
    if (Test-Path "$Root\$f") {
        Copy-Item "$Root\$f" -Destination "$Temp\$f"
    }
}

# 6. Создаём README с инструкцией
Write-Host "[6/6] README_MIGRATION.txt..." -ForegroundColor Yellow
$readme = @"
=== Wh40K MIGRATION PACKAGE ===
Собрано: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
Источник: $Root

Что внутри:
- chroma_db/         — RAG-база (12k+ документов)
- .streamlit/        — секреты (GigaChat ключ)
- gigachat_key.txt   — если был
- data/users/        — персонажи и чаты
- config.yaml        — конфигурация
- VERSION, CHANGELOG.md

КАК ВОССТАНОВИТЬ НА НОВОМ ПК:

1. Установи Python 3.13, Git, Notepad++.

2. Клонируй репо:
   cd /d C:\
   mkdir Projects
   cd Projects
   git clone https://github.com/Velxeor96/the-stories-of-the-cat-Bayun.git Wh40K
   cd Wh40K

3. Создай venv:
   python -m venv .venv
   .venv\Scripts\activate

4. Поставь зависимости:
   pip install --upgrade pip
   pip install -r requirements.txt
   pip install torch --index-url https://download.pytorch.org/whl/cpu
   pip install sentence-transformers

5. Распакуй ЭТОТ архив и скопируй папки/файлы в корень проекта C:\Projects\Wh40K\:
   - chroma_db\
   - .streamlit\
   - data\users\
   - config.yaml (если не в git)
   - gigachat_key.txt (если был)
   - VERSION, CHANGELOG.md (перезапиши)

6. Запуск:
   streamlit run app.py
"@
$readme | Out-File -FilePath "$Temp\README_MIGRATION.txt" -Encoding UTF8

# 7. Упаковка
Write-Host ""
Write-Host "Упаковка в архив..." -ForegroundColor Yellow
if (Test-Path $ZipPath) { Remove-Item $ZipPath -Force }
Compress-Archive -Path "$Temp\*" -DestinationPath $ZipPath -Force

# 8. Уборка
Remove-Item $Temp -Recurse -Force

# 9. Отчёт
$size = [math]::Round((Get-Item $ZipPath).Length / 1MB, 2)
Write-Host ""
Write-Host "=== ГОТОВО ===" -ForegroundColor Green
Write-Host "Архив: $ZipPath"
Write-Host "Размер: $size МБ"
Write-Host ""
Write-Host "Проверь, что в архиве: chroma_db, .streamlit, data/users, config.yaml" -ForegroundColor Cyan
Write-Host "Скопируй архив на новое устройство любым способом (флешка, облако)." -ForegroundColor Cyan