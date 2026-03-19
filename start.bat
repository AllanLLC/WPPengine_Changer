@echo off
title Persona Wallpaper Switcher
echo.
echo  ╔══════════════════════════════════════╗
echo  ║    PERSONA WALLPAPER SWITCHER        ║
echo  ╚══════════════════════════════════════╝
echo.

:: Install dependencies if needed
pip show flask-socketio >nul 2>&1
if %errorlevel% neq 0 (
    echo [*] Instalando dependencias...
    pip install -r requirements.txt
    echo.
)

echo [*] Iniciando servidor em http://127.0.0.1:5000
echo [*] Abrindo navegador...
echo.
start "" "http://127.0.0.1:5000"
python app.py
pause
