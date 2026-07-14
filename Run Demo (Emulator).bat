@echo off
title Virtual Android Demo
python "%~dp0run_demo.py"
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Python not found or script crashed.
    pause
)
