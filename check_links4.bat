@echo off
set "HTML_PATH=%~dp0index.html"
if not exist "%HTML_PATH%" (
    echo Index.html not found
    exit /b 1
)
rem Extract href URLs using findstr and PowerShell one-liner
for /f "delims=" %%U in ('powershell -NoProfile -Command "(Get-Content -Path '%HTML_PATH%' -Raw) -match 'href=\"([^\"]+)\"' | foreach { $matches[1] }' ") do (
    set "URL=%%U"
    echo Checking !URL! ...
    curl -I -s -m 10 "!URL!" | findstr /R "^HTTP/"
)
