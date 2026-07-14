@echo off
title APK Builder
python "%~dp0apk_builder.py"
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Python not found or script crashed.
    echo Make sure Python 3.8+ is installed: https://www.python.org/downloads/
    pause
)
