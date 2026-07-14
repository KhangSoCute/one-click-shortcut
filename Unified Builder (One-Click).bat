@echo off
title Unified Android Shortcut Creator
python "%~dp0unified_builder.py"
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Python not found or script crashed.
    pause
)
