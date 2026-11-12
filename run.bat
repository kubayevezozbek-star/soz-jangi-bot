@echo off
chcp 65001 > nul
title So'z Jangi Bot
echo ====================================================
echo          ⚔️ SO'Z JANGI TELEGRAM BOT ⚔️
echo ====================================================
echo.
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
    echo [INFO] Virtual muhit faollashtirilmoqda...
    ".venv\Scripts\python.exe" main.py
) else (
    echo [INFO] Tizim Python orqali ishga tushirilmoqda...
    python main.py
)

pause
