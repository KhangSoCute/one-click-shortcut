@echo off
title Shortcut Creator
python "%~dp0shortcut_creator.py"
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Python not found or script crashed.
    echo Make sure Python 3 is installed: https://www.python.org/downloads/
    pause
)
