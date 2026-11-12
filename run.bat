@echo off
title PromptBox 0.5
cd /d "%~dp0"
python app.py
if errorlevel 1 (
  echo.
  echo No se pudo iniciar PromptBox. Revisa Python.
  pause
)
