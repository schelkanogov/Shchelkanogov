@echo off
TITLE URL Validator - Personal Lending Page
echo Starting URL validation for index.html...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0extract_and_validate.ps1"
pause
