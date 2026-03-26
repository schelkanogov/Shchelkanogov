# ============================================
# DEPLOY LANDING PAGE (Fix for Cyrillic paths)
# ============================================

# Получаем текущую директорию (откуда запущен скрипт)
$repoDir = $PSScriptRoot

if (-Not $repoDir) {
    Write-Error "Please run the script directly, not by copy-pasting its contents."
    exit 1
}

$avatarSrc = "C:\Users\PC\.gemini\antigravity\brain\3cd6af62-12e6-4654-ab44-353292268ae1\media__1773804057044.jpg"
$avatarDst = Join-Path $repoDir "avatar.jpg"

Set-Location $repoDir
Write-Host "=== Working in: $repoDir ===" -ForegroundColor Cyan

# 1. Настройка git user (если не задано)
$userName = git config user.name 2>$null
if (-not $userName) {
    Write-Host "[1/5] Setting git user config..." -ForegroundColor Yellow
    git config user.name "Pavel Shchelkanogov"
    git config user.email "Schelkanogov@internet.ru"
} else {
    Write-Host "[1/5] Git user already configured: $userName" -ForegroundColor Green
}

# 2. Копируем avatar.jpg
if (-not (Test-Path $avatarDst)) {
    Write-Host "[2/5] Copying avatar photo..." -ForegroundColor Yellow
    Copy-Item -Path $avatarSrc -Destination $avatarDst -Force
    Write-Host "      Avatar copied successfully." -ForegroundColor Green
} else {
    Write-Host "[2/5] Avatar already exists." -ForegroundColor Green
}

# 3. git add
Write-Host "[3/5] Staging files..." -ForegroundColor Yellow
git add avatar.jpg index.html deploy.ps1
if ($LASTEXITCODE -ne 0) { Write-Error "git add failed!"; exit 1 }

# 4. git commit
Write-Host "[4/5] Committing..." -ForegroundColor Yellow
git commit -m "Deploy landing page - add avatar photo, update links, add consultation form"
if ($LASTEXITCODE -ne 0) {
    Write-Host "      Nothing to commit or commit failed. Trying push anyway..." -ForegroundColor Yellow
}

# 5. git push
Write-Host "[5/5] Pushing to GitHub..." -ForegroundColor Yellow
git push origin main
if ($LASTEXITCODE -ne 0) {
    Write-Host "      Trying 'git push origin master'..." -ForegroundColor Yellow
    git push origin master
    if ($LASTEXITCODE -ne 0) { Write-Error "git push failed!"; exit 1 }
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host "  DEPLOY COMPLETE!" -ForegroundColor Green
Write-Host "  Check: https://schelkanogov.github.io/Shchelkanogov/" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Green
